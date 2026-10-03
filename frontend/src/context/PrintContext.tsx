import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { applyTheme } from "../hooks/useThemePreference";

interface PrintJob {
  /** Becomes the browser's suggested PDF file name. */
  fileName: string;
  content: ReactNode;
}

const PrintContext = createContext<((job: PrintJob) => void) | null>(null);

/**
 * "Download PDF" without a PDF library: the content is rendered into a print-only
 * sheet outside the app, and the browser's print dialog saves it ("Save as PDF").
 * Text stays selectable and charts stay sharp. Always printed in the light theme.
 */
export function PrintProvider({ children }: { children: ReactNode }) {
  const [job, setJob] = useState<PrintJob | null>(null);

  useEffect(() => {
    if (!job) return;
    const root = document.documentElement;
    const previousTheme = root.dataset.theme;
    const previousTitle = document.title;

    const restore = () => {
      if (previousTheme === "light" || previousTheme === "dark") applyTheme(previousTheme);
      else applyTheme("system");
      delete root.dataset.printing;
      document.title = previousTitle;
      setJob(null);
    };

    applyTheme("light");
    root.dataset.printing = "true";
    document.title = job.fileName;
    window.addEventListener("afterprint", restore, { once: true });
    // Let the sheet (and its SVG charts) paint before the dialog opens.
    const frame = requestAnimationFrame(() => setTimeout(() => window.print(), 50));
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("afterprint", restore);
    };
  }, [job]);

  return (
    <PrintContext.Provider value={setJob}>
      {children}
      {job && createPortal(<div className="print-sheet">{job.content}</div>, document.body)}
    </PrintContext.Provider>
  );
}

export function usePrint(): (job: PrintJob) => void {
  const print = useContext(PrintContext);
  if (!print) throw new Error("usePrint must be used inside <PrintProvider>");
  return useCallback((job: PrintJob) => print(job), [print]);
}

/** "Parag Parikh vs HDFC!" -> "parag-parikh-vs-hdfc" for file names. */
export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 60);
}
