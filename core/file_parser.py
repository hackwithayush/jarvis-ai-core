"""
JARVIS Intelligence Grid — Universal File & Attachment Parser
Extracts deep context, structured data, and text from virtually any file format:
- Documents: PDF, DOCX, DOC, PPTX, XLSX, XLS, CSV, TSV, TXT, RTF, EPUB
- Developer & Code: PY, JS, TS, HTML, CSS, JSON, YAML, XML, SQL, SH, BAT, IPYNB, LOG, etc.
- Media: Images (dimensions, metadata), Audio/Video (container info, size)
- Archives: ZIP, TAR, GZ (manifest tree inspection)
- Fallback: Binary inspection with printable strings & checksums
"""
import os
import io
import re
import csv
import json
import zipfile
import tarfile
import hashlib
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("jarvis.file_parser")

# Optional advanced parsers
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class UniversalFileParser:
    """Enterprise-grade multi-format file parsing engine."""

    MAX_TEXT_LENGTH = 60000  # Cap extracted text to fit comfortably in LLM context windows
    MAX_TABLE_ROWS = 100

    CODE_AND_TEXT_EXTENSIONS = {
        # Text & Markdown
        "txt", "md", "markdown", "rst", "rtf", "log", "diff", "patch", "tex",
        # Web
        "html", "htm", "css", "scss", "sass", "less", "js", "jsx", "ts", "tsx", "vue", "svelte", "wasm",
        # Data & Config
        "json", "jsonl", "yaml", "yml", "xml", "toml", "ini", "cfg", "conf", "env", "properties",
        # Backend & Scripts
        "py", "sh", "bash", "zsh", "bat", "ps1", "sql", "rb", "php", "java", "kt", "scala",
        "c", "cpp", "cc", "cxx", "h", "hpp", "cs", "go", "rs", "swift", "m", "mm", "r", "lua", "dart",
        "asm", "s", "dockerfile", "makefile", "cmake"
    }

    @classmethod
    def parse_file(cls, filepath: str, original_filename: Optional[str] = None) -> Dict[str, Any]:
        """Entrypoint: Inspect, classify, and extract structured intelligence from any file."""
        if not os.path.exists(filepath):
            return {
                "status": "error",
                "filename": original_filename or os.path.basename(filepath),
                "error": "File does not exist on disk"
            }

        filename = original_filename or os.path.basename(filepath)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        filesize = os.path.getsize(filepath)

        result = {
            "filename": filename,
            "extension": ext,
            "size_bytes": filesize,
            "size_readable": cls._format_size(filesize),
            "file_type": "unknown",
            "text_content": "",
            "summary": "",
            "metadata": {}
        }

        try:
            # 1. Jupyter Notebooks
            if ext == "ipynb":
                cls._parse_notebook(filepath, result)

            # 2. PDF Documents
            elif ext == "pdf":
                cls._parse_pdf(filepath, result)

            # 3. Microsoft Word
            elif ext in ("docx", "doc"):
                cls._parse_docx(filepath, result)

            # 4. Microsoft Excel / Spreadsheets
            elif ext in ("xlsx", "xls"):
                cls._parse_excel(filepath, result)

            # 5. CSV / TSV
            elif ext in ("csv", "tsv"):
                cls._parse_csv_tsv(filepath, ext, result)

            # 6. Microsoft PowerPoint
            elif ext in ("pptx", "ppt"):
                cls._parse_pptx(filepath, result)

            # 7. Code & Plain Text
            elif ext in cls.CODE_AND_TEXT_EXTENSIONS or filename.lower() in ("dockerfile", "makefile", "license", "procfile", ".env"):
                cls._parse_plain_text(filepath, ext, result)

            # 8. Archive Files
            elif ext in ("zip", "tar", "gz", "tgz", "7z", "rar"):
                cls._parse_archive(filepath, ext, result)

            # 9. Images
            elif ext in ("png", "jpg", "jpeg", "gif", "webp", "bmp", "svg", "tiff", "ico"):
                cls._parse_image(filepath, ext, result)

            # 10. Audio & Video
            elif ext in ("mp3", "wav", "m4a", "ogg", "flac", "aac", "mp4", "mkv", "avi", "mov", "webm"):
                cls._parse_media(filepath, ext, result)

            # 11. Generic fallback for unknown extensions
            else:
                # Try reading as text first
                if not cls._try_read_as_text(filepath, result):
                    cls._parse_binary_fallback(filepath, result)

        except Exception as e:
            logger.error(f"Error parsing file {filename}: {e}", exc_info=True)
            result["text_content"] = f"[Error reading file: {str(e)}]"
            result["summary"] = f"File: {filename} ({result['size_readable']}) - Parsing Error: {str(e)}"

        # Generate summary if not already populated
        if not result["summary"]:
            snippet = result["text_content"][:400].replace("\n", " ").strip()
            result["summary"] = f"File: {filename} ({result['size_readable']}) | Type: {result['file_type']}\nContent Preview: {snippet}..."

        return result

    @classmethod
    def _parse_plain_text(cls, filepath: str, ext: str, result: Dict[str, Any]):
        """Read standard text/code with multi-encoding fallback."""
        text = cls._read_file_text_safe(filepath)
        result["file_type"] = f"Source/Text ({ext.upper() if ext else 'TXT'})"
        result["text_content"] = text[:cls.MAX_TEXT_LENGTH]
        lines = text.splitlines()
        result["metadata"]["line_count"] = len(lines)
        result["summary"] = f"File: {result['filename']} ({result['size_readable']}, {len(lines)} lines)\nPreview:\n" + "\n".join(lines[:15])

    @classmethod
    def _parse_notebook(cls, filepath: str, result: Dict[str, Any]):
        """Parse Jupyter Notebook cells."""
        result["file_type"] = "Jupyter Notebook"
        text = cls._read_file_text_safe(filepath)
        try:
            nb = json.loads(text)
            cells = nb.get("cells", [])
            extracted = [f"# Jupyter Notebook: {result['filename']}\nTotal Cells: {len(cells)}\n"]
            for idx, cell in enumerate(cells, 1):
                ctype = cell.get("cell_type", "unknown")
                source = "".join(cell.get("source", []))
                extracted.append(f"\n--- Cell {idx} [{ctype.upper()}] ---\n{source}")
            full_text = "\n".join(extracted)
            result["text_content"] = full_text[:cls.MAX_TEXT_LENGTH]
            result["metadata"]["cells_count"] = len(cells)
            result["summary"] = f"Jupyter Notebook '{result['filename']}' ({len(cells)} cells, {result['size_readable']})"
        except Exception:
            result["text_content"] = text[:cls.MAX_TEXT_LENGTH]

    @classmethod
    def _parse_pdf(cls, filepath: str, result: Dict[str, Any]):
        """Extract text and metadata from PDF documents."""
        result["file_type"] = "PDF Document"
        if PYPDF_AVAILABLE:
            try:
                reader = pypdf.PdfReader(filepath)
                num_pages = len(reader.pages)
                extracted_pages = []
                for pno, page in enumerate(reader.pages, 1):
                    ptext = page.extract_text() or ""
                    if ptext.strip():
                        extracted_pages.append(f"\n--- [Page {pno}/{num_pages}] ---\n{ptext.strip()}")
                
                full_text = f"Document: {result['filename']} (Total Pages: {num_pages})\n" + "\n".join(extracted_pages)
                result["text_content"] = full_text[:cls.MAX_TEXT_LENGTH]
                result["metadata"]["page_count"] = num_pages
                result["summary"] = f"PDF Document '{result['filename']}' ({num_pages} pages, {result['size_readable']})"
                return
            except Exception as e:
                logger.warning(f"pypdf extraction error for {filepath}: {e}")

        # Fallback: scan for printable PDF text stream
        text = cls._extract_raw_pdf_text(filepath)
        result["text_content"] = text[:cls.MAX_TEXT_LENGTH] or "[PDF contains scanned images or encrypted text]"
        result["summary"] = f"PDF Document '{result['filename']}' ({result['size_readable']})"

    @classmethod
    def _parse_docx(cls, filepath: str, result: Dict[str, Any]):
        """Extract paragraphs and tables from Word documents."""
        result["file_type"] = "Word Document (DOCX)"
        if DOCX_AVAILABLE:
            try:
                doc = docx.Document(filepath)
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                tables_data = []
                for t in doc.tables:
                    for row in t.rows:
                        row_vals = [cell.text.strip() for cell in row.cells]
                        tables_data.append(" | ".join(row_vals))
                
                body = "\n\n".join(paragraphs)
                if tables_data:
                    body += "\n\n--- Tables Extracted ---\n" + "\n".join(tables_data[:cls.MAX_TABLE_ROWS])
                    
                result["text_content"] = body[:cls.MAX_TEXT_LENGTH]
                result["metadata"]["paragraph_count"] = len(paragraphs)
                result["summary"] = f"Word Document '{result['filename']}' ({len(paragraphs)} paragraphs, {result['size_readable']})"
                return
            except Exception as e:
                logger.warning(f"python-docx extraction failed: {e}")

        # Fallback via XML inspection inside DOCX zip
        cls._parse_docx_xml_fallback(filepath, result)

    @classmethod
    def _parse_excel(cls, filepath: str, result: Dict[str, Any]):
        """Extract sheets and tabular data from Excel workbooks."""
        result["file_type"] = "Excel Spreadsheet (XLSX)"
        if OPENPYXL_AVAILABLE:
            try:
                wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
                sheets_output = []
                total_sheets = len(wb.sheetnames)
                for sname in wb.sheetnames:
                    sheet = wb[sname]
                    rows_text = []
                    count = 0
                    for row in sheet.iter_rows(values_only=True):
                        if count >= cls.MAX_TABLE_ROWS:
                            rows_text.append(f"... [Truncated at {cls.MAX_TABLE_ROWS} rows]")
                            break
                        if any(v is not None for v in row):
                            row_str = " | ".join([str(v) if v is not None else "" for v in row])
                            rows_text.append(row_str)
                            count += 1
                    sheets_output.append(f"\n--- Sheet: {sname} ({count} rows preview) ---\n" + "\n".join(rows_text))
                wb.close()
                result["text_content"] = f"Excel Workbook: {result['filename']} ({total_sheets} sheets)\n" + "\n".join(sheets_output)
                result["metadata"]["sheet_names"] = wb.sheetnames
                result["summary"] = f"Excel Workbook '{result['filename']}' ({total_sheets} sheets: {', '.join(wb.sheetnames)}, {result['size_readable']})"
                return
            except Exception as e:
                logger.warning(f"openpyxl failed: {e}")

        cls._parse_binary_fallback(filepath, result)

    @classmethod
    def _parse_csv_tsv(cls, filepath: str, ext: str, result: Dict[str, Any]):
        """Parse CSV and TSV tabular files."""
        result["file_type"] = "CSV/TSV Table"
        text = cls._read_file_text_safe(filepath)
        delimiter = "\t" if ext == "tsv" else ","
        try:
            reader = csv.reader(io.StringIO(text), delimiter=delimiter)
            rows = list(reader)
            total_rows = len(rows)
            preview_rows = rows[:cls.MAX_TABLE_ROWS]
            formatted = []
            for r in preview_rows:
                formatted.append(" | ".join(r))
            result["text_content"] = f"Table: {result['filename']} (Total Rows: {total_rows})\n" + "\n".join(formatted)
            result["metadata"]["row_count"] = total_rows
            result["summary"] = f"Tabular File '{result['filename']}' ({total_rows} rows, {result['size_readable']})"
        except Exception:
            result["text_content"] = text[:cls.MAX_TEXT_LENGTH]

    @classmethod
    def _parse_pptx(cls, filepath: str, result: Dict[str, Any]):
        """Parse PowerPoint PPTX slides by inspecting slide XML."""
        result["file_type"] = "PowerPoint Presentation (PPTX)"
        try:
            with zipfile.ZipFile(filepath, "r") as zf:
                slide_files = sorted([f for f in zf.namelist() if f.startswith("ppt/slides/slide") and f.endswith(".xml")])
                slides_text = []
                import xml.etree.ElementTree as ET
                for idx, sfile in enumerate(slide_files, 1):
                    xml_content = zf.read(sfile)
                    tree = ET.fromstring(xml_content)
                    texts = [elem.text for elem in tree.iter() if elem.text and elem.text.strip()]
                    if texts:
                        slides_text.append(f"\n--- [Slide {idx}/{len(slide_files)}] ---\n" + "\n".join(texts))
                full_text = f"PowerPoint Presentation: {result['filename']} ({len(slide_files)} slides)\n" + "\n".join(slides_text)
                result["text_content"] = full_text[:cls.MAX_TEXT_LENGTH]
                result["metadata"]["slide_count"] = len(slide_files)
                result["summary"] = f"PowerPoint '{result['filename']}' ({len(slide_files)} slides, {result['size_readable']})"
        except Exception as e:
            cls._parse_binary_fallback(filepath, result)

    @classmethod
    def _parse_archive(cls, filepath: str, ext: str, result: Dict[str, Any]):
        """Inspect and list archive contents."""
        result["file_type"] = f"Archive ({ext.upper()})"
        entries = []
        if ext == "zip":
            try:
                with zipfile.ZipFile(filepath, "r") as zf:
                    for info in zf.infolist()[:100]:
                        entries.append(f"{info.filename} ({cls._format_size(info.file_size)})")
                    result["metadata"]["file_count"] = len(zf.infolist())
            except Exception as e:
                entries.append(f"[Error reading zip: {e}]")
        elif ext in ("tar", "gz", "tgz"):
            try:
                mode = "r:gz" if ext in ("gz", "tgz") else "r"
                with tarfile.open(filepath, mode) as tf:
                    for member in tf.getmembers()[:100]:
                        entries.append(f"{member.name} ({cls._format_size(member.size)})")
                    result["metadata"]["file_count"] = len(tf.getmembers())
            except Exception as e:
                entries.append(f"[Error reading tar: {e}]")

        manifest = f"Archive Manifest: {result['filename']} (Total entries preview: {len(entries)})\n" + "\n".join(f"- {e}" for e in entries)
        result["text_content"] = manifest
        result["summary"] = f"Archive '{result['filename']}' ({result['size_readable']}, {result['metadata'].get('file_count', len(entries))} items)"

    @classmethod
    def _parse_image(cls, filepath: str, ext: str, result: Dict[str, Any]):
        """Extract visual metadata and execute multimodal vision analysis."""
        result["file_type"] = f"Image ({ext.upper()})"
        result["is_image"] = True
        meta = {}
        img_dims = ""
        if PIL_AVAILABLE:
            try:
                with Image.open(filepath) as img:
                    meta["format"] = img.format
                    meta["mode"] = img.mode
                    meta["width"] = img.width
                    meta["height"] = img.height
                    result["metadata"] = meta
                    img_dims = f"{img.width}x{img.height} {img.format}"
            except Exception:
                pass

        # Multimodal Vision Analysis: Attempt autonomous visual interpretation
        vision_description = ""
        try:
            from core.model_manager import ModelManager
            mm = ModelManager()
            prompt = (
                "Thoroughly analyze and describe this image. "
                "1. Identify the core subjects, scene, UI elements, charts, diagrams, or objects. "
                "2. Transcribe any readable text, code, numbers, labels, or error messages (OCR). "
                "3. Provide actionable context or key insights."
            )
            v_out = mm.generate_vision(prompt, filepath)
            if v_out and not str(v_out).startswith("Vision processing failed") and not str(v_out).startswith("Vision Node failure"):
                vision_description = v_out.strip()
        except Exception as e:
            logger.warning(f"UniversalFileParser vision analysis exception for {filepath}: {e}")

        dim_str = f" ({img_dims})" if img_dims else ""
        if vision_description:
            result["text_content"] = (
                f"[IMAGE ATTACHMENT: {result['filename']}{dim_str}, Size: {result['size_readable']}]\n"
                f"--- VISUAL RECOGNITION & OCR ANALYSIS ---\n"
                f"{vision_description}\n"
                f"--- END VISUAL ANALYSIS ---"
            )
            result["summary"] = f"Image '{result['filename']}'{dim_str}: {vision_description[:280]}..."
        else:
            result["text_content"] = f"[IMAGE ATTACHMENT]\nFilename: {result['filename']}\nResolution: {img_dims or 'Unknown'}\nFilesize: {result['size_readable']}"
            result["summary"] = f"Image '{result['filename']}'{dim_str} ({result['size_readable']})"

    @classmethod
    def _parse_media(cls, filepath: str, ext: str, result: Dict[str, Any]):
        """Extract audio/video container metadata."""
        is_audio = ext in ("mp3", "wav", "m4a", "ogg", "flac", "aac")
        result["file_type"] = "Audio File" if is_audio else "Video File"
        result["text_content"] = f"[MEDIA ATTACHMENT: {result['file_type']}]\nFilename: {result['filename']}\nFormat: {ext.upper()}\nSize: {result['size_readable']}"
        result["summary"] = f"{result['file_type']} '{result['filename']}' ({ext.upper()}, {result['size_readable']})"

    @classmethod
    def _parse_binary_fallback(cls, filepath: str, result: Dict[str, Any]):
        """Safe inspection of binary files with hash and printable strings."""
        result["file_type"] = "Binary / Data File"
        sha256 = cls._compute_sha256(filepath)
        strings = cls._extract_printable_strings(filepath, max_strings=30)
        
        info = [
            f"[BINARY FILE INSPECTION]",
            f"Filename: {result['filename']}",
            f"Size: {result['size_readable']}",
            f"SHA256: {sha256}",
            f"\n--- Extracted Printable Strings Preview ---",
            "\n".join(strings) if strings else "[No printable ASCII strings detected]"
        ]
        result["text_content"] = "\n".join(info)
        result["metadata"]["sha256"] = sha256
        result["summary"] = f"Binary File '{result['filename']}' ({result['size_readable']}, SHA256: {sha256[:12]}...)"

    @classmethod
    def _parse_docx_xml_fallback(cls, filepath: str, result: Dict[str, Any]):
        """XML fallback for docx files when python-docx is unavailable."""
        try:
            with zipfile.ZipFile(filepath, "r") as zf:
                if "word/document.xml" in zf.namelist():
                    xml_data = zf.read("word/document.xml").decode("utf-8", errors="ignore")
                    text_nodes = re.findall(r'<w:t[^>]*>(.*?)</w:t>', xml_data)
                    body = "".join(text_nodes)
                    result["text_content"] = body[:cls.MAX_TEXT_LENGTH]
                    result["summary"] = f"Word Document '{result['filename']}' ({result['size_readable']})"
                    return
        except Exception:
            pass
        cls._parse_binary_fallback(filepath, result)

    @classmethod
    def _try_read_as_text(cls, filepath: str, result: Dict[str, Any]) -> bool:
        """Attempt to read unknown file as text without throwing errors."""
        try:
            with open(filepath, "rb") as f:
                raw = f.read(4096)
                if b"\x00" in raw:
                    return False  # Null bytes indicate binary
            text = cls._read_file_text_safe(filepath)
            if text:
                cls._parse_plain_text(filepath, result["extension"], result)
                return True
        except Exception:
            pass
        return False

    @classmethod
    def _read_file_text_safe(cls, filepath: str) -> str:
        """Read text trying multiple common encodings."""
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"):
            try:
                with open(filepath, "r", encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception:
                break
        return ""

    @classmethod
    def _extract_raw_pdf_text(cls, filepath: str) -> str:
        """Regex scanner for text elements inside uncompressed PDF objects."""
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            matches = re.findall(rb'\((.*?)\)\s*Tj', data)
            lines = [m.decode("latin-1", errors="ignore") for m in matches if len(m) > 1]
            return "\n".join(lines[:1000])
        except Exception:
            return ""

    @classmethod
    def _extract_printable_strings(cls, filepath: str, max_strings: int = 30) -> list:
        """Extract readable ASCII strings from binary files."""
        try:
            with open(filepath, "rb") as f:
                content = f.read(65536)
            strings = re.findall(rb'[\x20-\x7E]{4,}', content)
            return [s.decode("latin-1") for s in strings[:max_strings]]
        except Exception:
            return []

    @classmethod
    def _compute_sha256(cls, filepath: str) -> str:
        """Compute SHA256 checksum."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Human-readable filesize."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


# Singleton instance
file_parser = UniversalFileParser()
