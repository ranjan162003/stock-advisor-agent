import { Fragment, type ReactNode } from "react";

/**
 * The small slice of Markdown the assistant writes: paragraphs, "-"/"1." lists,
 * "#" headings, | tables |, **bold**, *italic* and `code`. Renders React elements (never raw
 * HTML), so model output can't inject markup.
 */
export function ChatMarkdown({ text }: { text: string }) {
  return <div className="chat-markdown">{renderBlocks(text)}</div>;
}

type Block =
  | { kind: "paragraph"; lines: string[] }
  | { kind: "heading"; text: string }
  | { kind: "list"; ordered: boolean; items: string[] }
  | { kind: "table"; rows: string[][] };

const BULLET = /^\s*[-*•]\s+(.*)$/;
const NUMBERED = /^\s*\d+[.)]\s+(.*)$/;
const HEADING = /^\s*#{1,6}\s+(.*)$/;
const TABLE_ROW = /^\s*\|.*\|\s*$/;
const TABLE_DIVIDER = /^\s*\|?[\s:|-]+\|?\s*$/;

function renderBlocks(text: string): ReactNode[] {
  const blocks: Block[] = [];
  for (const line of text.replace(/\r\n/g, "\n").split("\n")) {
    const last = blocks[blocks.length - 1];
    const bullet = BULLET.exec(line);
    const numbered = bullet ? null : NUMBERED.exec(line);
    const heading = HEADING.exec(line);
    if (TABLE_ROW.test(line)) {
      if (TABLE_DIVIDER.test(line)) continue; // the |---|---| line under the header
      const cells = line.trim().slice(1, -1).split("|").map((cell) => cell.trim());
      if (last?.kind === "table") last.rows.push(cells);
      else blocks.push({ kind: "table", rows: [cells] });
    } else if (!line.trim()) {
      blocks.push({ kind: "paragraph", lines: [] });
    } else if (heading) {
      blocks.push({ kind: "heading", text: heading[1] });
    } else if (bullet || numbered) {
      const ordered = Boolean(numbered);
      const item = (bullet ?? numbered)![1];
      if (last?.kind === "list" && last.ordered === ordered) last.items.push(item);
      else blocks.push({ kind: "list", ordered, items: [item] });
    } else if (last?.kind === "paragraph") {
      last.lines.push(line.trim());
    } else if (last?.kind === "list" && /^\s{2,}/.test(line)) {
      last.items[last.items.length - 1] += " " + line.trim(); // wrapped list item
    } else {
      blocks.push({ kind: "paragraph", lines: [line.trim()] });
    }
  }

  return blocks
    .filter((b) => (b.kind === "paragraph" ? b.lines.length > 0 : true))
    .map((block, i) => {
      if (block.kind === "heading")
        return (
          <p key={i} className="chat-markdown__heading">
            {renderInline(block.text)}
          </p>
        );
      if (block.kind === "table") {
        const [header, ...body] = block.rows;
        return (
          <div key={i} className="table-scroll">
            <table className="chat-compare">
              <thead>
                <tr>
                  {header.map((cell, j) => (
                    <th key={j}>{renderInline(cell)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {body.map((row, r) => (
                  <tr key={r}>
                    {row.map((cell, j) =>
                      j === 0 ? (
                        <th key={j} scope="row">
                          {renderInline(cell)}
                        </th>
                      ) : (
                        <td key={j}>{renderInline(cell)}</td>
                      ),
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      if (block.kind === "list") {
        const List = block.ordered ? "ol" : "ul";
        return (
          <List key={i}>
            {block.items.map((item, j) => (
              <li key={j}>{renderInline(item)}</li>
            ))}
          </List>
        );
      }
      return (
        <p key={i}>
          {block.lines.map((line, j) => (
            <Fragment key={j}>
              {j > 0 && <br />}
              {renderInline(line)}
            </Fragment>
          ))}
        </p>
      );
    });
}

const INLINE = /(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*\s][^*]*\*)/g;

function renderInline(text: string): ReactNode[] {
  return text.split(INLINE).map((part, i) => {
    if (/^(\*\*|__).+\1$/.test(part)) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (/^`.+`$/.test(part)) return <code key={i}>{part.slice(1, -1)}</code>;
    if (/^\*.+\*$/.test(part)) return <em key={i}>{part.slice(1, -1)}</em>;
    return <Fragment key={i}>{part}</Fragment>;
  });
}
