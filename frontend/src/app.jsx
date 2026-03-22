// src/App.jsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar   from "./components/layout/Sidebar";
import Overview  from "./pages/Overview";
import Forecast  from "./pages/Forecast";
import Inventory from "./pages/Inventory";
import Order     from "./pages/Order";

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display: "flex", minHeight: "100vh" }}>
        <Sidebar />
        <main style={{ marginLeft: 220, flex: 1, minHeight: "100vh" }}>
          <Routes>
            <Route path="/"          element={<Overview  />} />
            <Route path="/forecast"  element={<Forecast  />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/orders"    element={<Order     />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}