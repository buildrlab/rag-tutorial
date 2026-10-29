"""Small, inspectable word-budget chunkers. Production needs a model tokenizer."""
import re
import uuid


def windows(text: str, size: int, overlap: int) -> list[str]:
    words = text.split()
    result = []
    for start in range(0, len(words), size - overlap):
        result.append(" ".join(words[start:start + size]))
        if start + size >= len(words):
            break
    return result


def split_text(text: str, strategy="sections", size=100, overlap=15) -> list[str]:
    if not 20 <= size <= 400 or not 0 <= overlap < size:
        raise ValueError("Use 20–400 words with overlap smaller than the chunk size.")
    if strategy == "fixed":
        return windows(text, size, overlap)
    if strategy not in {"sections", "paragraphs"}:
        raise ValueError("Unknown chunk strategy")
    # Sections deliberately never cross a heading; paragraphs accumulate to a budget.
    units = re.split(r"(?m)(?=^#{1,6} )", text) if strategy == "sections" else re.split(r"\n\s*\n", text)
    chunks, pending = [], ""
    for unit in units:
        unit = unit.strip()
        if not unit:
            continue
        if strategy == "sections":
            chunks.extend(windows(unit, size, overlap))
        elif len((pending + " " + unit).split()) <= size:
            pending = (pending + "\n\n" + unit).strip()
        else:
            if pending:
                chunks.append(pending)
                pending = ""
            pieces = windows(unit, size, overlap)
            chunks.extend(pieces[:-1])
            pending = pieces[-1]
    if pending:
        chunks.append(pending)
    return chunks


def chunk_documents(documents, strategy="sections", size=100, overlap=15):
    result = []
    for doc in documents:
        for number, text in enumerate(split_text(doc["text"], strategy, size, overlap)):
            identity = f'{doc["id"]}:{strategy}:{size}:{overlap}:{number}:{text}'
            result.append({**doc, "id": str(uuid.uuid5(uuid.NAMESPACE_URL, identity)),
                           "document_id": doc["id"], "text": text, "chunk": number + 1,
                           "words": len(text.split())})
    return result
