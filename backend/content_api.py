"""Content file browser API - separate module to avoid syntax conflicts."""
import base64
import os

CONTENT_ROOT = os.path.expanduser("~")
CONTENT_MAX_FILE = 5 * 1024 * 1024  # 5MB max read

CONTENT_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico'}
CONTENT_HIDE_DIRS = {'.git', '__pycache__', 'node_modules', '.cache', '.local', '.gnupg', '.ssh'}
CONTENT_HIDE_FILES = {'.DS_Store', '.env', '.env.local', 'id_rsa', 'id_ed25519'}


def content_safe_path(requested):
    """Resolve path and ensure it stays within CONTENT_ROOT."""
    if not requested:
        return CONTENT_ROOT
    requested = os.path.expanduser(requested)
    if not requested.startswith('/'):
        requested = os.path.join(CONTENT_ROOT, requested)
    resolved = os.path.realpath(requested)
    if not resolved.startswith(os.path.realpath(CONTENT_ROOT)):
        return None
    return resolved


def content_list_directory(dir_path):
    """List directory entries with metadata."""
    entries = []
    try:
        for name in sorted(os.listdir(dir_path)):
            if name.startswith('.') and name in CONTENT_HIDE_DIRS:
                continue
            if name in CONTENT_HIDE_FILES:
                continue
            full_path = os.path.join(dir_path, name)
            try:
                st = os.stat(full_path)
            except OSError:
                continue
            is_dir = os.path.isdir(full_path)
            ext = '' if is_dir else os.path.splitext(name)[1].lower()
            entries.append({
                "name": name,
                "path": full_path,
                "is_dir": is_dir,
                "size": st.st_size if not is_dir else 0,
                "ext": ext,
                "modified": st.st_mtime,
            })
    except PermissionError:
        return None
    return entries


def content_get_file(file_path):
    """Read a file and return its content + type info."""
    try:
        st = os.stat(file_path)
    except OSError as e:
        return {"error": str(e)}

    if st.st_size > CONTENT_MAX_FILE:
        return {"type": "binary", "size": st.st_size, "ext": os.path.splitext(file_path)[1].lower()}

    ext = os.path.splitext(file_path)[1].lower()

    if ext in CONTENT_IMAGE_EXTS:
        try:
            with open(file_path, 'rb') as f:
                data = f.read(st.st_size)
            mime_map = {
                '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.gif': 'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml',
            }
            return {
                "type": "image",
                "mime": mime_map.get(ext, 'application/octet-stream'),
                "content": base64.b64encode(data).decode(),
                "ext": ext,
                "path": file_path,
            }
        except Exception as e:
            return {"error": str(e)}

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        return {"error": str(e)}

    return {
        "type": "text",
        "content": content,
        "ext": ext,
        "path": file_path,
        "size": st.st_size,
    }


def content_save_file(file_path, content):
    """Save content to a file."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
