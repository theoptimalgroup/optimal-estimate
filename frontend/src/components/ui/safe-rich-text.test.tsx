import React from "react";
import { describe, expect, it } from "vitest";
import { JSDOM } from "jsdom";
import { renderToStaticMarkup } from "react-dom/server";

import { looksLikeHtml, prepareRichTextValue, renderEworksRichText, SafeRichText, sanitizeRichTextHtml } from "@/components/ui/safe-rich-text";

const SCREENSHOT_MALFORMED_QUOTE_DESCRIPTION =
  '<span style="text-decoration: underline;"><strong>Access</strong></span>:&nbsp;<br /><br />' +
  '</span style="text-decoration: underline;"><strong>Quote</strong></span>: Please quote for Velux window replacement in the kitchen area.<br /><br />' +
  '</span style="text-decoration: underline;"><strong>Info</strong></span>: Booked by&nbsp;<br /><br /></span>' +
  '</span style="text-decoration: underline;"><strong>Contact</strong></span>: Miss Brenda - 07960696064';

function visibleText(markup: string): string {
  return new JSDOM(markup).window.document.body.textContent ?? "";
}

describe("sanitizeRichTextHtml", () => {
  it("renders strong text for safe HTML formatting", () => {
    const sanitized = sanitizeRichTextHtml("<strong>Access</strong>");
    expect(sanitized).toContain("Access");
    expect(sanitized.toLowerCase()).toContain("strong");
  });

  it("preserves line breaks", () => {
    const sanitized = sanitizeRichTextHtml("Line one<br />Line two");
    expect(sanitized.toLowerCase()).toContain("br");
    expect(sanitized).toContain("Line one");
    expect(sanitized).toContain("Line two");
  });

  it("preserves ordered list markup for rendering", () => {
    const sanitized = sanitizeRichTextHtml("<ol><li>First item</li><li>Second item</li></ol>");
    expect(sanitized).toContain("First item");
    expect(sanitized).toContain("Second item");
    expect(sanitized.toLowerCase()).toContain("ol");
    expect(sanitized.toLowerCase()).toContain("li");
  });

  it("removes script tags", () => {
    const sanitized = sanitizeRichTextHtml('<script>alert("xss")</script><p>Safe text</p>');
    expect(sanitized.toLowerCase()).not.toContain("script");
    expect(sanitized).not.toContain("alert");
    expect(sanitized).toContain("Safe text");
  });

  it("removes javascript links", () => {
    const sanitized = sanitizeRichTextHtml('<a href="javascript:alert(1)">Click me</a>');
    expect(sanitized.toLowerCase()).not.toContain("javascript:");
    expect(sanitized).toContain("Click me");
  });

  it("strips unsafe inline styles from eWorks markup", () => {
    const sanitized = sanitizeRichTextHtml(
      '<span style="text-decoration: underline; color: red; font-size: 20px;"><strong>Access</strong></span>'
    );
    expect(sanitized).not.toContain("style=");
    expect(sanitized).not.toContain("font-size");
    expect(sanitized).not.toContain("color:");
    expect(sanitized).toContain("Access");
  });

  it("converts underline spans to semantic underline markup", () => {
    const sanitized = sanitizeRichTextHtml(
      '<span style="text-decoration: underline;"><strong>Access</strong></span>'
    );
    expect(sanitized.toLowerCase()).toMatch(/<(u|strong)/);
    expect(sanitized).toContain("Access");
    expect(sanitized).not.toContain("style=");
  });

  it("allows safe http links with blank target", () => {
    const sanitized = sanitizeRichTextHtml('<a href="https://example.com/terms">Terms link</a>');
    expect(sanitized).toContain('href="https://example.com/terms"');
    expect(sanitized).toContain('target="_blank"');
    expect(sanitized).toContain('rel="noopener noreferrer"');
  });
});

describe("looksLikeHtml", () => {
  it("detects HTML markup", () => {
    expect(looksLikeHtml("<p>Hello</p>")).toBe(true);
    expect(looksLikeHtml("Plain text only")).toBe(false);
  });

  it("detects entity-encoded HTML markup", () => {
    expect(looksLikeHtml("&lt;strong&gt;Access&lt;/strong&gt;")).toBe(true);
    expect(looksLikeHtml("&lt;br /&gt;")).toBe(true);
  });
});

describe("prepareRichTextValue", () => {
  it("decodes entity-encoded HTML before sanitization", () => {
    const encoded =
      "&lt;span style=&quot;text-decoration: underline;&quot;&gt;&lt;strong&gt;Access&lt;/strong&gt;&lt;/span&gt;";
    const prepared = prepareRichTextValue(encoded);
    expect(prepared.isHtml).toBe(true);
    expect(prepared.content).toContain("<strong>Access</strong>");
  });
});

describe("renderEworksRichText", () => {
  it("falls back to readable plain text for malformed screenshot-style HTML", () => {
    const rendered = renderEworksRichText(SCREENSHOT_MALFORMED_QUOTE_DESCRIPTION);
    expect(rendered.mode === "html" || rendered.mode === "plain").toBe(true);
    const text =
      rendered.mode === "html"
        ? visibleText(`<div>${rendered.html}</div>`)
        : rendered.text;
    expect(text).toContain("Access");
    expect(text).toContain("Quote");
    expect(text).toContain("Velux window replacement");
    expect(text).not.toContain("<span");
    expect(text).not.toContain("</span");
    expect(text).not.toContain("<br");
    expect(text).not.toContain("&nbsp;");
  });
});

describe("SafeRichText", () => {
  it("renders formatted HTML without raw tags in output", () => {
    const markup = renderToStaticMarkup(
      <SafeRichText
        value={'<span style="text-decoration: underline;"><strong>Access</strong></span><br />&nbsp;<br />Quote text'}
        testId="rich-text"
      />
    );
    const text = visibleText(markup);
    expect(text).toContain("Access");
    expect(text).toContain("Quote text");
    expect(text).not.toContain("<span");
    expect(text).not.toContain("&nbsp;");
    expect(text).not.toContain("<br");
  });

  it("renders entity-encoded eWorks HTML safely", () => {
    const encoded =
      "&lt;strong&gt;Access&lt;/strong&gt;&lt;br /&gt;&lt;br /&gt;Quote&lt;br /&gt;QUOTE ONLY Fire door inspection";
    const text = visibleText(renderToStaticMarkup(<SafeRichText value={encoded} testId="rich-text" />));
    expect(text).toContain("Access");
    expect(text).toContain("Quote");
    expect(text).not.toContain("&lt;");
    expect(text.toLowerCase()).not.toContain("script");
  });

  it("renders plain text with line breaks", () => {
    const text = visibleText(
      renderToStaticMarkup(<SafeRichText value={"Access\n\nQuote\nInfo line"} testId="rich-text" />)
    );
    expect(text).toContain("Access");
    expect(text).toContain("Quote");
    expect(text).toContain("Info line");
    expect(text).not.toContain("<span");
  });

  it("removes script tags from rendered output", () => {
    const text = visibleText(
      renderToStaticMarkup(
        <SafeRichText value={'<script>alert("x")</script><strong>Access</strong>'} testId="rich-text" />
      )
    );
    expect(text).toContain("Access");
    expect(text.toLowerCase()).not.toContain("script");
    expect(text).not.toContain("alert");
  });

  it("renders eWorks Step 1 quote description sample without raw HTML tags", () => {
    const text = visibleText(
      renderToStaticMarkup(
        <SafeRichText value={SCREENSHOT_MALFORMED_QUOTE_DESCRIPTION} testId="quote-description-rich-text" />
      )
    );
    expect(text).toContain("Access");
    expect(text).toContain("Quote");
    expect(text).toContain("Velux window replacement");
    expect(text).not.toContain("<span");
    expect(text).not.toContain("</span");
    expect(text).not.toContain("<br");
    expect(text).not.toContain("&nbsp;");
  });
});
