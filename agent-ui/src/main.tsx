import { renderMarkdown } from "@a2ui/markdown-it";
import { setMarkdownRenderer } from "@a2ui/web_core/v0_9/basic_catalog";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./index.css";
import { App } from "./App.tsx";

setMarkdownRenderer(renderMarkdown);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
