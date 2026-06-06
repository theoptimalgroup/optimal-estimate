"use client";

import DOMPurify from "isomorphic-dompurify";

import {
  cleanHtmlToReadableText,
  decodeHtmlEntitiesRepeated,
  isHtmlLike,
  normalizeMalformedEworksHtml,
} from "@/lib/html-text";

const ALLOWED_TAGS = [
  "p",
  "br",
  "strong",
  "b",
  "em",
  "i",
  "u",
  "ol",
  "ul",
  "li",
  "span",
  "a",
  "table",
  "tr",
  "td",
  "th",
];

const FORBID_TAGS = ["script", "iframe", "object", "embed", "form", "input", "button", "style"];

const SAFE_HREF_PATTERN = /^(?:https?:|mailto:)/i;

const RAW_MARKUP_IN_TEXT = /<\/?[a-z]|&nbsp;|&lt;\/?[a-z]/i;

/** True when the string appears to contain HTML markup (raw, entity-encoded, or malformed). */
export function looksLikeHtml(value: string): boolean {
  return isHtmlLike(value);
}

/** Decode entities, normalize malformed eWorks tags, and detect HTML. */
export function prepareRichTextValue(raw: string): { isHtml: boolean; content: string } {
  const content = normalizeMalformedEworksHtml(decodeHtmlEntitiesRepeated(raw.trim(), 3));
  return { isHtml: isHtmlLike(content), content };
}

/** Convert common eWorks underline spans to semantic <u> before sanitization. */
function preprocessEworksHtml(html: string): string {
  return normalizeMalformedEworksHtml(html).replace(
    /<span\b[^>]*style\s*=\s*(["'])[^"']*text-decoration\s*:\s*underline[^"']*\1[^>]*>([\s\S]*?)<\/span>/gi,
    "<u>$2</u>"
  );
}

function configureLinkHook(): void {
  DOMPurify.addHook("afterSanitizeAttributes", (node) => {
    if (node.tagName !== "A" || !node.hasAttribute("href")) {
      return;
    }
    const href = node.getAttribute("href") ?? "";
    if (!SAFE_HREF_PATTERN.test(href.trim())) {
      node.removeAttribute("href");
      return;
    }
    node.setAttribute("target", "_blank");
    node.setAttribute("rel", "noopener noreferrer");
  });
}

function removeLinkHook(): void {
  DOMPurify.removeHook("afterSanitizeAttributes");
}

/** Sanitize eWorks rich text HTML for safe rendering. Exported for unit tests. */
export function sanitizeRichTextHtml(raw: string): string {
  const preprocessed = preprocessEworksHtml(raw.trim());
  configureLinkHook();
  try {
    return DOMPurify.sanitize(preprocessed, {
      ALLOWED_TAGS,
      ALLOWED_ATTR: ["href", "target", "rel"],
      ALLOW_DATA_ATTR: false,
      ALLOWED_URI_REGEXP: SAFE_HREF_PATTERN,
      FORBID_TAGS,
    });
  } finally {
    removeLinkHook();
  }
}

function sanitizedHtmlStillShowsRawMarkup(sanitizedHtml: string): boolean {
  if (typeof DOMParser === "undefined") {
    return RAW_MARKUP_IN_TEXT.test(sanitizedHtml);
  }
  const text = new DOMParser().parseFromString(sanitizedHtml, "text/html").body.textContent ?? "";
  return RAW_MARKUP_IN_TEXT.test(text);
}

export type EworksRichTextRender =
  | { mode: "html"; html: string }
  | { mode: "plain"; text: string };

/** Fail-safe renderer for eWorks rich text (sanitize HTML or fall back to readable plain text). */
export function renderEworksRichText(value: string | null | undefined): EworksRichTextRender {
  if (value == null || value.trim() === "") {
    return { mode: "plain", text: "" };
  }

  const { isHtml, content } = prepareRichTextValue(String(value));
  if (!isHtml) {
    return { mode: "plain", text: cleanHtmlToReadableText(content) };
  }

  const sanitized = sanitizeRichTextHtml(content);
  if (!sanitized.trim() || sanitizedHtmlStillShowsRawMarkup(sanitized)) {
    return { mode: "plain", text: cleanHtmlToReadableText(content) };
  }

  return { mode: "html", html: sanitized };
}

const richTextBoxClass =
  "max-h-96 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 " +
  "[&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5 " +
  "[&_p]:mb-2 [&_strong]:font-semibold [&_b]:font-semibold [&_u]:underline [&_em]:italic [&_i]:italic " +
  "[&_a]:text-blue-700 [&_a]:underline";

const richTextInlineClass =
  "text-sm leading-relaxed text-inherit " +
  "[&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5 " +
  "[&_p]:mb-2 [&_strong]:font-semibold [&_b]:font-semibold [&_u]:underline [&_em]:italic [&_i]:italic " +
  "[&_a]:text-blue-700 [&_a]:underline";

export function SafeRichText({
  value,
  emptyText = "Not available",
  className,
  testId,
  variant = "boxed",
}: {
  value: string | null | undefined;
  emptyText?: string;
  className?: string;
  testId?: string;
  variant?: "boxed" | "inline";
}) {
  const rendered = renderEworksRichText(value);
  const baseClass = variant === "inline" ? richTextInlineClass : richTextBoxClass;

  if (rendered.mode === "plain" && rendered.text.trim() === "") {
    return (
      <p className={`text-sm text-slate-500 ${className ?? ""}`} data-testid={testId}>
        {emptyText}
      </p>
    );
  }

  if (rendered.mode === "html") {
    return (
      <div
        className={`${baseClass} ${className ?? ""}`}
        data-testid={testId}
        dangerouslySetInnerHTML={{ __html: rendered.html }}
      />
    );
  }

  return (
    <div
      className={`${baseClass} whitespace-pre-wrap ${className ?? ""}`}
      data-testid={testId}
    >
      {rendered.text}
    </div>
  );
}
