/** Detect HTML markup in a string (raw, entity-encoded, or malformed eWorks tags). */
export function isHtmlLike(value: string): boolean {
  if (/<\/?[a-z][\s\S]*>/i.test(value)) return true;
  if (/&lt;\/?[a-z]/i.test(value)) return true;
  if (/<\/span\s+[^>]+>/i.test(value)) return true;
  return false;
}

/** Decode common HTML entities (single pass). */
export function decodeHtmlEntities(text: string): string {
  if (typeof document !== "undefined") {
    const el = document.createElement("textarea");
    el.innerHTML = text;
    return el.value;
  }
  return text
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number(code)));
}

/** Decode HTML entities repeatedly (handles double-encoded eWorks payloads). */
export function decodeHtmlEntitiesRepeated(text: string, maxPasses = 3): string {
  let current = text;
  for (let pass = 0; pass < maxPasses; pass += 1) {
    const decoded = decodeHtmlEntities(current);
    if (decoded === current) break;
    current = decoded;
  }
  return current;
}

/** Fix common malformed eWorks markup such as </span style="..."> used as a section opener. */
export function normalizeMalformedEworksHtml(html: string): string {
  let out = html;
  out = out.replace(/<\/span\s+([^>]+)>/gi, "<span $1>");
  out = out.replace(/<\/strong\s+([^>]+)>/gi, "<strong $1>");
  out = out.replace(/<\/u\s+([^>]+)>/gi, "<u $1>");
  return out;
}

function normalizeSpaces(text: string): string {
  return text.replace(/\u00a0/g, " ");
}

function collapseBlankLines(text: string): string {
  return normalizeSpaces(text)
    .replace(/\r\n/g, "\n")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n[ \t]+/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function stripAllTags(value: string): string {
  return decodeHtmlEntities(value.replace(/<[^>]*>/g, " "));
}

function htmlToPlainTextWithDom(html: string): string {
  const doc = new DOMParser().parseFromString(html, "text/html");
  const lines: string[] = [];

  const walk = (node: Node, listContext?: { ordered: boolean; index: number }) => {
    if (node.nodeType === Node.TEXT_NODE) {
      const text = node.textContent ?? "";
      if (text) lines.push(text);
      return;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return;

    const el = node as Element;
    const tag = el.tagName.toLowerCase();

    if (tag === "script" || tag === "style") return;

    if (tag === "br") {
      lines.push("\n");
      return;
    }

    if (tag === "li") {
      const inner = collectInlineText(el).trim();
      if (inner) {
        const prefix = listContext?.ordered ? `${listContext.index}. ` : "• ";
        lines.push(`${prefix}${inner}\n`);
        if (listContext?.ordered) listContext.index += 1;
      }
      return;
    }

    if (tag === "ol") {
      const ctx = { ordered: true, index: 1 };
      el.childNodes.forEach((child) => walk(child, ctx));
      lines.push("\n");
      return;
    }

    if (tag === "ul") {
      el.childNodes.forEach((child) => walk(child, { ordered: false, index: 0 }));
      lines.push("\n");
      return;
    }

    if (["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "table", "section"].includes(tag)) {
      el.childNodes.forEach((child) => walk(child, listContext));
      lines.push("\n");
      return;
    }

    el.childNodes.forEach((child) => walk(child, listContext));
  };

  const collectInlineText = (el: Element): string => {
    let out = "";
    el.childNodes.forEach((child) => {
      if (child.nodeType === Node.TEXT_NODE) {
        out += child.textContent ?? "";
      } else if (child.nodeType === Node.ELEMENT_NODE) {
        const childTag = (child as Element).tagName.toLowerCase();
        if (childTag === "br") {
          out += "\n";
        } else if (childTag !== "script" && childTag !== "style") {
          out += collectInlineText(child as Element);
        }
      }
    });
    return out;
  };

  doc.body.childNodes.forEach((child) => walk(child));
  return collapseBlankLines(lines.join("").replace(/[ \t]+/g, " "));
}

function htmlToPlainTextFallback(html: string): string {
  let text = html;
  text = text.replace(/<script[\s\S]*?<\/script>/gi, "");
  text = text.replace(/<style[\s\S]*?<\/style>/gi, "");
  text = text.replace(/<br\s*\/?>/gi, "\n");
  text = text.replace(/<\/p>/gi, "\n");
  text = text.replace(/<\/div>/gi, "\n");
  text = text.replace(/<\/h[1-6]>/gi, "\n");
  text = text.replace(/<li[^>]*>/gi, "\n• ");
  text = text.replace(/<\/li>/gi, "\n");
  text = text.replace(/<[^>]+>/g, "");
  return collapseBlankLines(decodeHtmlEntities(text));
}

/** Convert HTML rich text to readable plain text. */
export function htmlToPlainText(value: string): string {
  const trimmed = decodeHtmlEntitiesRepeated(value.trim(), 3);
  const normalized = normalizeMalformedEworksHtml(trimmed);
  if (!isHtmlLike(normalized)) return collapseBlankLines(decodeHtmlEntities(normalized));

  if (typeof DOMParser !== "undefined") {
    try {
      return htmlToPlainTextWithDom(normalized);
    } catch {
      return htmlToPlainTextFallback(normalized);
    }
  }
  return htmlToPlainTextFallback(normalized);
}

/** Readable plain text for display when rich HTML is malformed or unsafe to render. */
export function cleanHtmlToReadableText(value: string | null | undefined): string {
  if (value == null || value === "") return "";
  return htmlToPlainText(String(value));
}

/** Compact single-line preview for list cards (collapses whitespace; full text stays in forms). */
export function compactCardPreviewText(value: string | null | undefined): string {
  const text = cleanHtmlToReadableText(value);
  if (!text) return "";
  return text.replace(/\s+/g, " ").trim();
}

/** Plain text suitable for textarea/input values (strips HTML, normalizes whitespace). */
export function cleanRichTextForTextarea(value: string | null | undefined): string {
  if (value == null || value === "") return "";
  return cleanHtmlToReadableText(value);
}

/** Strip HTML from short labels such as product names. */
export function stripHtmlFromLabel(value: string | null | undefined): string {
  if (value == null || value === "") return "";
  const raw = String(value).trim();
  if (!isHtmlLike(raw)) return raw;
  return stripAllTags(raw).replace(/\s+/g, " ").trim();
}
