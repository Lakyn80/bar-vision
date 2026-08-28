import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import {
  QueryClientProvider,
} from "@tanstack/react-query";
import { BrowserRouter } from "react-router";
import { registerSW } from "virtual:pwa-register";

import App from "./App";
import { queryClient } from "./app/query-client";
import "./index.css";


registerSW({
  immediate: true,
});


const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element not found.");
}


createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);