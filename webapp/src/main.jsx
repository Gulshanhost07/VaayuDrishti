import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import Dashboard from "./pages/Dashboard.jsx";
import Report from "./pages/Report.jsx";
import Submit from "./pages/Submit.jsx";
import Admin from "./pages/Admin.jsx";

const path = location.pathname;
const Page = path.includes("report") ? Report
  : path.includes("submit") ? Submit
  : path.includes("admin") ? Admin
  : Dashboard;

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Page />
  </React.StrictMode>
);
