import { describe, expect, it } from "vitest";

import {
  cleanHtmlToReadableText,
  cleanRichTextForTextarea,
  compactCardPreviewText,
  decodeHtmlEntitiesRepeated,
  htmlToPlainText,
  isHtmlLike,
  normalizeMalformedEworksHtml,
  stripHtmlFromLabel,
} from "@/lib/html-text";

export const SCREENSHOT_MALFORMED_QUOTE_DESCRIPTION =
  '<span style="text-decoration: underline;"><strong>Access</strong></span>:&nbsp;<br /><br />' +
  '</span style="text-decoration: underline;"><strong>Quote</strong></span>: Please quote for Velux window replacement in the kitchen area.<br /><br />' +
  '</span style="text-decoration: underline;"><strong>Info</strong></span>: Booked by&nbsp;<br /><br /></span>' +
  '</span style="text-decoration: underline;"><strong>Contact</strong></span>: Miss Brenda - 07960696064';

const EWORKS_SAMPLE =
  '<span style="text-decoration: underline;"><strong>Access</strong></span><br />&nbsp;<br />' +
  '<span style="text-decoration: underline;"><strong>Quote</strong></span><br />Reinstate bath panel<br />' +
  "<ol><li>First answer</li><li>Second answer</li></ol>";

describe("isHtmlLike", () => {
  it("detects HTML markup", () => {
    expect(isHtmlLike("<p>Hello</p>")).toBe(true);
    expect(isHtmlLike("Plain text only")).toBe(false);
  });
});

describe("normalizeMalformedEworksHtml", () => {
  it("converts malformed closing span tags with attributes into opening spans", () => {
    const normalized = normalizeMalformedEworksHtml(
      '</span style="text-decoration: underline;"><strong>Quote</strong></span>'
    );
    expect(normalized).toContain('<span style="text-decoration: underline;"><strong>Quote</strong></span>');
    expect(normalized).not.toContain("</span style");
  });
});

describe("decodeHtmlEntitiesRepeated", () => {
  it("decodes double-encoded HTML entities", () => {
    const decoded = decodeHtmlEntitiesRepeated("&lt;strong&gt;Access&lt;/strong&gt;", 3);
    expect(decoded).toBe("<strong>Access</strong>");
  });
});

describe("cleanHtmlToReadableText", () => {
  it("handles screenshot-style malformed eWorks quote description", () => {
    const text = cleanHtmlToReadableText(SCREENSHOT_MALFORMED_QUOTE_DESCRIPTION);
    expect(text).toContain("Access");
    expect(text).toContain("Quote");
    expect(text).toContain("Please quote for Velux window replacement");
    expect(text).toContain("Booked by");
    expect(text).toContain("Miss Brenda");
    expect(text).not.toMatch(/<span|<\/span|<br|&nbsp;|<strong/i);
  });
});

describe("htmlToPlainText", () => {
  it("converts underline headings to readable labels", () => {
    const text = htmlToPlainText(
      '<span style="text-decoration: underline;"><strong>Access</strong></span><br />Caretaker on site'
    );
    expect(text).toContain("Access");
    expect(text).toContain("Caretaker on site");
    expect(text).not.toContain("<span");
    expect(text).not.toContain("&nbsp;");
  });

  it("converts br to newlines", () => {
    const text = htmlToPlainText("Line one<br />Line two");
    expect(text).toContain("Line one");
    expect(text).toContain("Line two");
    expect(text).not.toContain("<br");
  });

  it("converts list items to readable lines", () => {
    const text = htmlToPlainText("<ol><li>First item</li><li>Second item</li></ol>");
    expect(text).toContain("First item");
    expect(text).toContain("Second item");
    expect(text).not.toContain("<li");
    expect(text).not.toContain("<ol");
  });

  it("decodes nbsp entities", () => {
    const text = htmlToPlainText("Hello&nbsp;world");
    expect(text).toBe("Hello world");
  });

  it("removes script tags", () => {
    const text = htmlToPlainText('<script>alert("xss")</script><p>Safe text</p>');
    expect(text).not.toContain("script");
    expect(text).not.toContain("alert");
    expect(text).toContain("Safe text");
  });

  it("handles eWorks-style description blocks", () => {
    const text = htmlToPlainText(EWORKS_SAMPLE);
    expect(text).toContain("Access");
    expect(text).toContain("Quote");
    expect(text).toContain("Reinstate bath panel");
    expect(text).toContain("First answer");
    expect(text).not.toMatch(/<span|<br|&nbsp;|<ol/i);
  });
});

describe("cleanRichTextForTextarea", () => {
  it("returns plain text suitable for textarea values", () => {
    const text = cleanRichTextForTextarea(EWORKS_SAMPLE);
    expect(text).not.toContain("<");
    expect(text).not.toContain("&nbsp;");
  });

  it("passes through plain text unchanged aside from trimming", () => {
    expect(cleanRichTextForTextarea("  Plain scope  ")).toBe("Plain scope");
  });
});

describe("stripHtmlFromLabel", () => {
  it("strips HTML from product names", () => {
    expect(stripHtmlFromLabel("<strong>Plant Room</strong>")).toBe("Plant Room");
    expect(stripHtmlFromLabel("Window Repair")).toBe("Window Repair");
  });
});

describe("compactCardPreviewText", () => {
  it("collapses whitespace and strips HTML for card previews", () => {
    const preview = compactCardPreviewText(
      "<strong>SCOPE OF WORK</strong><br /><br />Line one.<br /><br />Line two.",
    );
    expect(preview).toBe("SCOPE OF WORK Line one. Line two.");
    expect(preview).not.toContain("<");
    expect(preview).not.toContain("\n");
  });
});
