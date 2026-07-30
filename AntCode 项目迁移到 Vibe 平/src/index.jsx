import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import "./theme.js";
import { HashRouter } from 'react-router-dom';

// 动态注入 Leaflet CSS 样式，避免组件内反复 import 出错
const leafletCss = document.createElement('link');
leafletCss.rel = 'stylesheet';
leafletCss.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
document.head.appendChild(leafletCss);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>
);