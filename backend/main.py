"""
File: main.py
Description: FastAPI backend for localization upload, editing, and sync workflows.
Author: zhangdadi
Created: 2026-03-10
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hmac
import html
from pathlib import Path
import re
import shutil
from typing import Literal
from xml.etree import ElementTree as ET

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
import jwt
from pydantic import BaseModel, Field
import yaml

PlatformType = Literal["ios", "android"]
LanguageCode = Literal["en", "ar", "tr"]

LANGUAGES: tuple[LanguageCode, ...] = ("en", "ar", "tr")
NON_ENGLISH_LANGUAGES: tuple[LanguageCode, ...] = ("ar", "tr")

LANGUAGE_DIR_MAP: dict[PlatformType, dict[LanguageCode, str]] = {
    "ios": {
        "en": "en.lproj",
        "ar": "ar.lproj",
        "tr": "tr.lproj",
    },
    "android": {
        "en": "values",
        "ar": "values-ar",
        "tr": "values-tr",
    },
}

PLATFORM_EXTENSION: dict[PlatformType, str] = {
    "ios": ".strings",
    "android": ".xml",
}

PREFERRED_FILE_NAME: dict[PlatformType, str] = {
    "ios": "Localizable.strings",
    "android": "strings.xml",
}

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
OLD_ENGLISH_DIR = STORAGE_DIR / "_old_english"
AUTH_CONFIG_PATH = BASE_DIR / "config.yaml"
AUTH_COOKIE_NAME = "access_token"
AUTH_ALGORITHM = "HS256"
PUBLIC_API_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/logout",
}


class SavePayload(BaseModel):
    platform: PlatformType
    language: LanguageCode
    relative_path: str
    content: str


class EditorRow(BaseModel):
    key: str = Field(default="")
    en: str = Field(default="")
    ar: str = Field(default="")
    tr: str = Field(default="")


class EditorSavePayload(BaseModel):
    platform: PlatformType
    relative_path: str
    rows: list[EditorRow]


class LoginPayload(BaseModel):
    username: str
    password: str


def load_auth_settings() -> tuple[str, int, dict[str, str]]:
    if not AUTH_CONFIG_PATH.exists():
        raise RuntimeError(f"Auth config file is missing: {AUTH_CONFIG_PATH}")

    try:
        raw = yaml.safe_load(AUTH_CONFIG_PATH.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RuntimeError(f"Failed to parse auth config yaml: {exc}") from exc

    auth_data = raw.get("auth") if isinstance(raw, dict) else None
    if not isinstance(auth_data, dict):
        raise RuntimeError("Invalid auth config: missing 'auth' section")

    jwt_secret_raw = auth_data.get("jwt_secret")
    jwt_secret = str(jwt_secret_raw).strip() if jwt_secret_raw is not None else ""
    if not jwt_secret:
        raise RuntimeError("Invalid auth config: 'auth.jwt_secret' is empty")

    jwt_exp_raw = auth_data.get("jwt_exp_minutes", 480)
    try:
        jwt_exp_minutes = int(jwt_exp_raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Invalid auth config: 'auth.jwt_exp_minutes' must be an integer") from exc
    if jwt_exp_minutes <= 0:
        raise RuntimeError("Invalid auth config: 'auth.jwt_exp_minutes' must be greater than 0")

    users_raw = auth_data.get("users")
    if not isinstance(users_raw, list):
        raise RuntimeError("Invalid auth config: 'auth.users' must be a list")

    users: dict[str, str] = {}
    for item in users_raw:
        if not isinstance(item, dict):
            continue
        if item.get("enabled", True) is False:
            continue

        username_raw = item.get("username")
        password_raw = item.get("password")
        username = str(username_raw).strip() if username_raw is not None else ""
        password = str(password_raw) if password_raw is not None else ""

        if not username or not password:
            continue
        users[username] = password

    if not users:
        raise RuntimeError("Invalid auth config: no enabled user with username and password")

    return jwt_secret, jwt_exp_minutes, users


AUTH_JWT_SECRET, AUTH_JWT_EXP_MINUTES, AUTH_USERS = load_auth_settings()

app = FastAPI(title="Localization Collaboration Service", version="1.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for platform_name, lang_map in LANGUAGE_DIR_MAP.items():
    for language_dir in lang_map.values():
        (STORAGE_DIR / platform_name / language_dir).mkdir(parents=True, exist_ok=True)


def sanitize_segment(value: str) -> str:
    clean = value.strip().replace("\\", "/").strip("/")
    if not clean:
        return ""
    if any(token in {".", ".."} for token in clean.split("/")):
        raise HTTPException(status_code=400, detail="Path contains invalid segments")
    return clean


def safe_join(base: Path, relative_path: str) -> Path:
    cleaned = sanitize_segment(relative_path)
    candidate = (base / cleaned).resolve()
    base_resolved = base.resolve()
    if base_resolved not in candidate.parents and candidate != base_resolved:
        raise HTTPException(status_code=400, detail="Path traversal is not allowed")
    return candidate


def get_language_root(platform: PlatformType, language: LanguageCode) -> Path:
    return STORAGE_DIR / platform / LANGUAGE_DIR_MAP[platform][language]


def read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def verify_login(username: str, password: str) -> bool:
    expected = AUTH_USERS.get(username)
    if expected is None:
        return False
    return hmac.compare_digest(expected, password)


def create_access_token(username: str) -> str:
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=AUTH_JWT_EXP_MINUTES)
    payload = {
        "sub": username,
        "exp": expire_at,
    }
    return jwt.encode(payload, AUTH_JWT_SECRET, algorithm=AUTH_ALGORITHM)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, AUTH_JWT_SECRET, algorithms=[AUTH_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Login expired") from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid login token") from exc

    username = payload.get("sub")
    if not isinstance(username, str) or not username.strip():
        raise HTTPException(status_code=401, detail="Invalid login token")
    if username not in AUTH_USERS:
        raise HTTPException(status_code=401, detail="User is disabled or removed")
    return username


def get_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header:
        return None

    prefix = "bearer "
    if not auth_header.lower().startswith(prefix):
        return None

    token = auth_header[len(prefix):].strip()
    return token or None


def get_authenticated_user(request: Request) -> str:
    bearer_token = get_bearer_token(request)
    if bearer_token:
        return decode_access_token(bearer_token)

    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    return decode_access_token(token)


@app.middleware("http")
async def auth_guard(request: Request, call_next):
    path = request.url.path

    if request.method == "OPTIONS":
        return await call_next(request)
    if not path.startswith("/api/"):
        return await call_next(request)
    if path in PUBLIC_API_PATHS:
        return await call_next(request)

    try:
        get_authenticated_user(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return await call_next(request)


def list_relative_files(platform: PlatformType, language: LanguageCode) -> list[str]:
    root = get_language_root(platform, language)
    extension = PLATFORM_EXTENSION[platform]
    files: list[str] = []

    for item in root.rglob(f"*{extension}"):
        if item.is_file():
            files.append(item.relative_to(root).as_posix())

    files.sort()
    return files


def normalize_keys(keys: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for key in keys:
        clean = key.strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        normalized.append(clean)

    return normalized


def extract_keys_from_content(platform: PlatformType, content: str) -> list[str] | None:
    try:
        parsed = parse_translation_content(platform, content)
    except ValueError:
        return None
    return normalize_keys(list(parsed.keys()))


def read_platform_english_keys(platform: PlatformType) -> list[str] | None:
    english_files = list_relative_files(platform, "en")
    if not english_files:
        return None

    root = get_language_root(platform, "en")
    target_file = safe_join(root, english_files[0])
    content = read_text_safe(target_file)
    return extract_keys_from_content(platform, content)


def get_old_english_file_path(platform: PlatformType) -> Path:
    extension = PLATFORM_EXTENSION[platform]
    return OLD_ENGLISH_DIR / platform / f"old_en{extension}"


def backup_current_english_file(platform: PlatformType) -> None:
    english_files = list_relative_files(platform, "en")
    if not english_files:
        return

    root = get_language_root(platform, "en")
    source_file = safe_join(root, english_files[0])
    backup_file = get_old_english_file_path(platform)
    backup_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_file, backup_file)


def read_old_english_keys(platform: PlatformType) -> list[str] | None:
    backup_file = get_old_english_file_path(platform)
    if not backup_file.exists() or not backup_file.is_file():
        return None

    content = read_text_safe(backup_file)
    return extract_keys_from_content(platform, content)


def get_platform_new_keys(platform: PlatformType) -> list[str]:
    current_keys = read_platform_english_keys(platform)
    old_keys = read_old_english_keys(platform)
    if not current_keys or old_keys is None:
        return []

    old_key_set = set(old_keys)
    return [key for key in current_keys if key not in old_key_set]


def clear_language_files(platform: PlatformType, language: LanguageCode) -> list[str]:
    root = get_language_root(platform, language)
    extension = PLATFORM_EXTENSION[platform]
    removed: list[str] = []

    for item in root.rglob(f"*{extension}"):
        if not item.is_file():
            continue
        removed.append(item.relative_to(root).as_posix())
        item.unlink()

    removed.sort()
    return removed


def normalize_file_stem(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def resolve_language_relative_path(
    platform: PlatformType,
    language: LanguageCode,
    preferred_relative_path: str,
) -> str | None:
    files = list_relative_files(platform, language)
    if not files:
        return None

    if preferred_relative_path in files:
        return preferred_relative_path

    preferred_lower = preferred_relative_path.lower()
    for candidate in files:
        if candidate.lower() == preferred_lower:
            return candidate

    preferred_name = Path(preferred_relative_path).name
    preferred_stem = normalize_file_stem(Path(preferred_name).stem)
    preferred_ext = Path(preferred_name).suffix.lower()

    if preferred_stem:
        stem_matched: list[str] = []
        for candidate in files:
            candidate_name = Path(candidate).name
            candidate_stem = normalize_file_stem(Path(candidate_name).stem)
            candidate_ext = Path(candidate_name).suffix.lower()
            if candidate_ext == preferred_ext and candidate_stem == preferred_stem:
                stem_matched.append(candidate)
        if len(stem_matched) == 1:
            return stem_matched[0]

    if len(files) == 1:
        return files[0]

    return None


def choose_editor_relative_path(platform: PlatformType) -> str:
    preferred_name = PREFERRED_FILE_NAME[platform]
    english_files = list_relative_files(platform, "en")

    if english_files:
        if preferred_name in english_files:
            return preferred_name
        return english_files[0]

    merged: set[str] = set()
    for language in LANGUAGES:
        merged.update(list_relative_files(platform, language))

    if not merged:
        return ""

    if preferred_name in merged:
        return preferred_name

    return sorted(merged)[0]


IOS_LINE_PATTERN = re.compile(r'^\s*"((?:\\.|[^"\\])*)"\s*=\s*"((?:\\.|[^"\\])*)"\s*;\s*$')
IOS_ESCAPE_PATTERN = re.compile(r'\\([nrt"\\])')
IOS_UNESCAPE_MAP = {
    "n": "\n",
    "r": "\r",
    "t": "\t",
    '"': '"',
    "\\": "\\",
}


def unescape_ios_value(value: str) -> str:
    return IOS_ESCAPE_PATTERN.sub(lambda match: IOS_UNESCAPE_MAP[match.group(1)], value)


def escape_ios_value(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def parse_ios_strings(content: str) -> dict[str, str]:
    data: dict[str, str] = {}

    for line in content.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("//")
            or stripped.startswith("/*")
            or stripped.startswith("*")
        ):
            continue

        match = IOS_LINE_PATTERN.match(stripped)
        if not match:
            continue

        key = unescape_ios_value(match.group(1))
        value = unescape_ios_value(match.group(2))
        data[key] = value

    return data


def parse_android_xml(content: str) -> dict[str, str]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError(f"XML parse failed: {exc}") from exc

    data: dict[str, str] = {}
    for node in root.findall("string"):
        key = (node.attrib.get("name") or "").strip()
        if not key:
            continue
        data[key] = node.text or ""

    return data


def parse_translation_content(platform: PlatformType, content: str) -> dict[str, str]:
    if platform == "ios":
        return parse_ios_strings(content)
    return parse_android_xml(content)


def serialize_ios_rows(rows: list[dict[str, str]], language: LanguageCode) -> str:
    lines: list[str] = []
    for row in rows:
        key = row["key"].strip()
        if not key:
            continue
        value = row.get(language, "")
        lines.append(f'"{escape_ios_value(key)}" = "{escape_ios_value(value)}";')

    if not lines:
        return ""

    return "\n".join(lines) + "\n"


def serialize_android_rows(rows: list[dict[str, str]], language: LanguageCode) -> str:
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<resources>"]

    for row in rows:
        key = row["key"].strip()
        if not key:
            continue
        value = row.get(language, "")
        escaped_key = html.escape(key, quote=True)
        escaped_value = html.escape(value, quote=False)
        lines.append(f'    <string name="{escaped_key}">{escaped_value}</string>')

    lines.append("</resources>")
    return "\n".join(lines) + "\n"


def serialize_translation_rows(
    platform: PlatformType,
    rows: list[dict[str, str]],
    language: LanguageCode,
) -> str:
    if platform == "ios":
        return serialize_ios_rows(rows, language)
    return serialize_android_rows(rows, language)


def get_opposite_platform(platform: PlatformType) -> PlatformType:
    if platform == "ios":
        return "android"
    return "ios"


def write_rows_to_existing_files(
    platform: PlatformType,
    relative_path: str,
    rows: list[dict[str, str]],
    languages: tuple[LanguageCode, ...] = LANGUAGES,
) -> tuple[list[str], list[str]]:
    saved_languages: list[str] = []
    skipped_languages: list[str] = []

    for language in languages:
        resolved_path = resolve_language_relative_path(platform, language, relative_path)
        if not resolved_path:
            skipped_languages.append(language)
            continue

        root = get_language_root(platform, language)
        target_file = safe_join(root, resolved_path)
        content = serialize_translation_rows(platform, rows, language)
        target_file.write_text(content, encoding="utf-8")
        saved_languages.append(language)

    return saved_languages, skipped_languages


def build_non_english_sync_map(rows: list[dict[str, str]]) -> dict[tuple[str, LanguageCode], str]:
    sync_map: dict[tuple[str, LanguageCode], str] = {}

    for row in rows:
        english_value = row.get("en", "").strip()
        if not english_value:
            continue

        for language in NON_ENGLISH_LANGUAGES:
            translation = row.get(language, "")
            if not translation.strip():
                continue
            sync_map[(english_value, language)] = translation

    return sync_map


def sync_non_english_to_other_platform(
    source_platform: PlatformType,
    source_rows: list[dict[str, str]],
) -> dict[str, str | int | list[str]]:
    target_platform = get_opposite_platform(source_platform)
    target_relative_path = choose_editor_relative_path(target_platform)

    if not target_relative_path:
        return {
            "target_platform": target_platform,
            "target_relative_path": "",
            "synced_rows": 0,
            "saved_languages": [],
        }

    target_rows, target_uploaded_languages = build_editor_rows(
        target_platform,
        target_relative_path,
    )

    if not target_rows:
        return {
            "target_platform": target_platform,
            "target_relative_path": target_relative_path,
            "synced_rows": 0,
            "saved_languages": [],
        }

    sync_map = build_non_english_sync_map(source_rows)
    if not sync_map:
        return {
            "target_platform": target_platform,
            "target_relative_path": target_relative_path,
            "synced_rows": 0,
            "saved_languages": [],
        }

    changed = False
    synced_rows = 0

    for row in target_rows:
        english_value = row.get("en", "").strip()
        if not english_value:
            continue

        row_changed = False
        for language in NON_ENGLISH_LANGUAGES:
            if not target_uploaded_languages.get(language):
                continue
            mapped = sync_map.get((english_value, language))
            if mapped is None:
                continue
            if row.get(language, "") == mapped:
                continue
            row[language] = mapped
            row_changed = True

        if row_changed:
            changed = True
            synced_rows += 1

    if not changed:
        return {
            "target_platform": target_platform,
            "target_relative_path": target_relative_path,
            "synced_rows": 0,
            "saved_languages": [],
        }

    saved_languages, _ = write_rows_to_existing_files(
        target_platform,
        target_relative_path,
        target_rows,
        languages=NON_ENGLISH_LANGUAGES,
    )

    return {
        "target_platform": target_platform,
        "target_relative_path": target_relative_path,
        "synced_rows": synced_rows,
        "saved_languages": saved_languages,
    }


def build_editor_rows(platform: PlatformType, relative_path: str) -> tuple[list[dict[str, str]], dict[LanguageCode, bool]]:
    merged: dict[str, dict[str, str]] = {}
    uploaded: dict[LanguageCode, bool] = {"en": False, "ar": False, "tr": False}

    for language in LANGUAGES:
        resolved_path = resolve_language_relative_path(platform, language, relative_path)
        if not resolved_path:
            continue

        root = get_language_root(platform, language)
        target_file = safe_join(root, resolved_path)

        uploaded[language] = True
        content = read_text_safe(target_file)
        try:
            values = parse_translation_content(platform, content)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"{language} file format error: {exc}",
            ) from exc

        for key, value in values.items():
            if key not in merged:
                merged[key] = {
                    "key": key,
                    "en": "",
                    "ar": "",
                    "tr": "",
                }
            merged[key][language] = value

    rows = list(merged.values())
    return rows, uploaded


def normalize_editor_rows(rows: list[EditorRow]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    index_map: dict[str, int] = {}

    for row in rows:
        key = row.key.strip()
        if not key:
            continue

        item = {
            "key": key,
            "en": row.en,
            "ar": row.ar,
            "tr": row.tr,
        }

        if key in index_map:
            normalized[index_map[key]] = item
        else:
            index_map[key] = len(normalized)
            normalized.append(item)

    return normalized


@app.post("/api/auth/login")
def auth_login(payload: LoginPayload, response: Response) -> dict[str, str]:
    username = payload.username.strip()
    if not username or not verify_login(username, payload.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(username)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=AUTH_JWT_EXP_MINUTES * 60,
        path="/",
    )
    return {
        "message": "Login successful",
        "username": username,
        "access_token": token,
        "token_type": "Bearer",
    }


@app.get("/api/auth/me")
def auth_me(request: Request) -> dict[str, str | bool]:
    username = get_authenticated_user(request)
    return {"authenticated": True, "username": username}


@app.post("/api/auth/logout")
def auth_logout(response: Response) -> dict[str, str]:
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/")
    return {"message": "Logged out"}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/files")
def list_files(
    platform: PlatformType = Query(..., description="Platform type"),
    language: LanguageCode = Query(..., description="Language code"),
) -> dict[str, list[dict[str, str | int]]]:
    root = get_language_root(platform, language)
    files: list[dict[str, str | int]] = []

    for item in root.rglob("*"):
        if not item.is_file():
            continue
        stat = item.stat()
        files.append(
            {
                "relative_path": item.relative_to(root).as_posix(),
                "size": stat.st_size,
                "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )

    files.sort(key=lambda item: item["relative_path"])
    return {"files": files}


@app.get("/api/download")
def download_file(
    platform: PlatformType = Query(..., description="Platform type"),
    language: LanguageCode = Query(..., description="Language code"),
    relative_path: str = Query(..., description="Relative file path"),
) -> FileResponse:
    root = get_language_root(platform, language)
    target_file = safe_join(root, relative_path)

    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=target_file,
        filename=target_file.name,
        media_type="application/octet-stream",
    )


@app.post("/api/upload")
async def upload_file(
    platform: PlatformType = Form(...),
    language: LanguageCode = Form(...),
    upload_file: UploadFile = File(...),
) -> dict[str, str]:
    original_name = Path(upload_file.filename or "").name
    if not original_name:
        raise HTTPException(status_code=400, detail="Filename cannot be empty")

    extension = Path(original_name).suffix.lower()
    expected_extension = PLATFORM_EXTENSION[platform]

    if extension != expected_extension:
        if platform == "ios":
            raise HTTPException(status_code=400, detail="iOS supports only .strings files")
        raise HTTPException(status_code=400, detail="android supports only .xml files")

    upload_bytes = await upload_file.read()
    if language == "en":
        backup_current_english_file(platform)

    root = get_language_root(platform, language)
    clear_language_files(platform, language)
    target_file = root / original_name

    with target_file.open("wb") as buffer:
        buffer.write(upload_bytes)

    return {
        "message": "Upload successful. Existing file for this platform and language was replaced.",
        "relative_path": target_file.relative_to(root).as_posix(),
    }


@app.get("/api/file-content")
def read_file_content(
    platform: PlatformType = Query(...),
    language: LanguageCode = Query(...),
    relative_path: str = Query(...),
) -> dict[str, str]:
    root = get_language_root(platform, language)
    target_file = safe_join(root, relative_path)

    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "relative_path": target_file.relative_to(root).as_posix(),
        "content": read_text_safe(target_file),
    }


@app.post("/api/file-content")
def save_file_content(payload: SavePayload) -> dict[str, str]:
    root = get_language_root(payload.platform, payload.language)
    target_file = safe_join(root, payload.relative_path)

    extension = target_file.suffix.lower()
    expected_extension = PLATFORM_EXTENSION[payload.platform]
    if extension != expected_extension:
        raise HTTPException(status_code=400, detail="Target file type is not supported")

    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(payload.content, encoding="utf-8")

    return {
        "message": "Saved successfully",
        "relative_path": target_file.relative_to(root).as_posix(),
    }


@app.get("/api/editor-table")
def get_editor_table(
    platform: PlatformType = Query(..., description="Platform type"),
) -> dict[str, str | list[dict[str, str]] | dict[str, bool] | list[str]]:
    relative_path = choose_editor_relative_path(platform)

    if not relative_path:
        return {
            "relative_path": "",
            "rows": [],
            "uploaded_languages": {
                "en": False,
                "ar": False,
                "tr": False,
            },
            "new_keys": [],
        }

    rows, uploaded = build_editor_rows(platform, relative_path)
    new_keys = get_platform_new_keys(platform)

    return {
        "relative_path": relative_path,
        "rows": rows,
        "uploaded_languages": uploaded,
        "new_keys": new_keys,
    }


@app.post("/api/editor-table")
def save_editor_table(
    payload: EditorSavePayload,
) -> dict[str, str | int | list[str] | dict[str, str | int | list[str]]]:
    relative_path = sanitize_segment(payload.relative_path)
    if not relative_path:
        raise HTTPException(status_code=400, detail="Missing editable target file")

    expected_extension = PLATFORM_EXTENSION[payload.platform]
    if not relative_path.lower().endswith(expected_extension):
        raise HTTPException(status_code=400, detail="Target file type does not match platform")

    rows = normalize_editor_rows(payload.rows)

    saved_languages, skipped_languages = write_rows_to_existing_files(
        payload.platform,
        relative_path,
        rows,
        languages=LANGUAGES,
    )

    if not saved_languages:
        raise HTTPException(
            status_code=400,
            detail="No source file is available to save on this platform. Please upload the language file first.",
        )

    sync_result = sync_non_english_to_other_platform(payload.platform, rows)

    return {
        "message": "Saved successfully",
        "relative_path": relative_path,
        "saved_languages": saved_languages,
        "skipped_languages": skipped_languages,
        "cross_platform_sync": sync_result,
    }
