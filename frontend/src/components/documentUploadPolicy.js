export const DOCUMENT_EXTENSIONS = Object.freeze(["pdf", "docx", "txt", "md"]);
export const DOCUMENT_ACCEPT = DOCUMENT_EXTENSIONS.map((extension) => `.${extension}`).join(",");
export const MAX_DOCUMENT_BYTES = 10 * 1024 * 1024;

export function validateDocumentFile(file) {
  if (!file) return "Choose a document to upload.";

  const extension = file.name.includes(".") ? file.name.split(".").pop().toLowerCase() : "";
  if (!DOCUMENT_EXTENSIONS.includes(extension)) {
    const displayExtension = extension ? `'.${extension}'` : "without an extension";
    return `Unsupported file type ${displayExtension}. Allowed: ${DOCUMENT_EXTENSIONS.join(", ")}`;
  }

  if (file.size > MAX_DOCUMENT_BYTES) return "File exceeds 10MB limit";
  return null;
}
