// src/services/api.js
// All calls to the FastAPI backend

import axios from "axios";

const BASE = axios.create({
  baseURL: process.env.REACT_APP_API_URL || "http://localhost:8000",
  timeout: 120000,
});

export const api = {
  // Health
  health: () => BASE.get("/health"),
  pipelineStatus: () => BASE.get("/pipeline/status"),

  // SKUs
  getSkus: () => BASE.get("/skus"),

  // Forecast
  getForecastAll: (horizon = 30) => BASE.get(`/forecast/all?horizon=${horizon}`),
  getForecastSku: (skuId, horizon = 30) => BASE.get(`/forecast/${skuId}?horizon=${horizon}`),

  // Inventory
  getInventory: () => BASE.get("/inventory"),
  getInventorySku: (skuId) => BASE.get(`/inventory/${skuId}`),

  // Purchase Orders
  getOrders: () => BASE.get("/orders"),
  getCriticalOrders: () => BASE.get("/orders/critical"),
};