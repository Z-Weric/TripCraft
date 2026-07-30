function injectTailwindTheme() {
  const style = document.createElement('style');
  style.type = 'text/tailwindcss';
  style.textContent = `
    @theme {
      --color-background: #FBF7F0;
      --color-background-secondary: #FFF9F0;
      --color-background-tertiary: #F5EEE0;
      
      --color-primary: #C9622A;
      --color-primary-dark: #A04A1E;
      --color-primary-light: #EFA882;
      --color-primary-muted: #D4A484;
      
      --color-foreground: #2C1810;
      --color-foreground-secondary: #5A4032;
      --color-foreground-tertiary: #8B7355;
      --color-foreground-disabled: #BFA98F;
      
      --color-border: #D4C5B0;
      --color-border-light: #E8DFD0;
      --color-border-dark: #8B7355;
      
      --color-success: #6B8E6B;
      --color-warning: #C9A227;
      --color-error: #B85450;
      --color-info: #7A8B99;
      
      --radius-sm: 4px;
      --radius-md: 8px;
      --radius-lg: 16px;
      
      --font-display: 'Georgia', 'Times New Roman', 'Noto Serif SC', 'Songti SC', serif;
      --font-body: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', sans-serif;
      --font-mono: 'SF Mono', 'Consolas', 'Monaco', 'Courier New', monospace;
    }

    body {
      background-color: #FBF7F0;
      color: #2C1810;
      font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      background-image: 
        /* 1. 航海罗盘水印 - 右上角，不循环，固定在右上方，半透明复古感 */
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300' viewBox='0 0 280 280' fill='none' stroke='%232C1810' stroke-width='0.5' stroke-dasharray='2%2C4' opacity='0.025'%3E%3Ccircle cx='140' cy='140' r='130' /%3E%3Ccircle cx='140' cy='140' r='90' /%3E%3Ccircle cx='140' cy='140' r='50' /%3E%3Cline x1='10' y1='140' x2='270' y2='140' /%3E%3Cline x1='140' y1='10' x2='140' y2='270' /%3E%3Cpath d='M140%2C5 L144%2C136 L140%2C140 L136%2C136 Z' fill='%232C1810' opacity='0.5' stroke-dasharray='0' /%3E%3Cpath d='M140%2C275 L144%2C144 L140%2C140 L136%2C144 Z' fill='%232C1810' opacity='0.5' stroke-dasharray='0' /%3E%3Cpath d='M5%2C140 L136%2C144 L140%2C140 L136%2C136 Z' fill='%232C1810' opacity='0.5' stroke-dasharray='0' /%3E%3Cpath d='M275%2C140 L144%2C144 L140%2C140 L144%2C136 Z' fill='%232C1810' opacity='0.5' stroke-dasharray='0' /%3E%3Cline x1='50' y1='50' x2='230' y2='230' /%3E%3Cline x1='50' y1='230' x2='230' y2='50' /%3E%3C/svg%3E"),
        /* 2. 航海罗盘水印 - 左下角，不循环，固定在左下方 */
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='240' height='240' viewBox='0 0 240 240' fill='none' stroke='%232C1810' stroke-width='0.4' stroke-dasharray='3%2C3' opacity='0.02'%3E%3Ccircle cx='120' cy='120' r='110' /%3E%3Ccircle cx='120' cy='120' r='75' /%3E%3Ccircle cx='120' cy='120' r='40' /%3E%3Cline x1='5' y1='120' x2='235' y2='120' /%3E%3Cline x1='120' y1='5' x2='120' y2='235' /%3E%3Cpath d='M120%2C5 L123%2C117 L120%2C120 L117%2C117 Z' fill='%232C1810' opacity='0.4' stroke-dasharray='0' /%3E%3Cpath d='M120%2C235 L123%2C123 L120%2C120 L117%2C123 Z' fill='%232C1810' opacity='0.4' stroke-dasharray='0' /%3E%3Cline x1='40' y1='40' x2='200' y2='200' /%3E%3Cline x1='40' y1='200' x2='200' y2='40' /%3E%3C/svg%3E"),
        /* 3. 复古雕花蕾丝/古典大马士革平铺花纹 */
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140' viewBox='0 0 120 120' opacity='0.012'%3E%3Cpath d='M60%2C0 C45%2C15 15%2C45 0%2C60 C15%2C75 45%2C105 60%2C120 C75%2C105 105%2C75 120%2C60 C105%2C45 75%2C15 60%2C0 Z M60%2C8 C74%2C22 106%2C54 112%2C60 C106%2C66 74%2C98 60%2C112 C46%2C98 14%2C66 8%2C60 C14%2C54 46%2C22 60%2C8 Z' fill='%232C1810' /%3E%3Cpath d='M60%2C30 C50%2C40 40%2C50 30%2C60 C40%2C70 50%2C80 60%2C90 C70%2C80 80%2C70 90%2C60 C80%2C50 70%2C40 60%2C30 Z M60%2C38 C66%2C44 76%2C54 82%2C60 C76%2C66 66%2C76 60%2C82 C54%2C76 44%2C66 38%2C60 C44%2C54 54%2C44 60%2C38 Z' fill='%232C1810' /%3E%3Ccircle cx='60' cy='60' r='5' fill='%232C1810' /%3E%3Ccircle cx='0' cy='0' r='2' fill='%232C1810' /%3E%3Ccircle cx='120' cy='0' r='2' fill='%232C1810' /%3E%3Ccircle cx='0' cy='120' r='2' fill='%232C1810' /%3E%3Ccircle cx='120' cy='120' r='2' fill='%232C1810' /%3E%3C/svg%3E"),
        /* 4. 细微复古纵向纸质纤维线条纹理 */
        repeating-linear-gradient(
          90deg,
          transparent,
          transparent 4px,
          rgba(44, 24, 16, 0.006) 4px,
          rgba(44, 24, 16, 0.006) 8px
        ),
        /* 5. 原有的横向明信片纸张纹路 */
        repeating-linear-gradient(
          0deg,
          transparent,
          transparent 2px,
          rgba(44, 24, 16, 0.008) 2px,
          rgba(44, 24, 16, 0.008) 4px
        );
      background-position: calc(100% - 60px) 140px, 60px calc(100% - 140px), center, center, center;
      background-repeat: no-repeat, no-repeat, repeat, repeat, repeat;
      background-attachment: fixed, fixed, scroll, scroll, scroll;
    }

    /* 修复 Leaflet css 与 antd 自带的样式冲突 */
    .leaflet-container {
      font-family: -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* 3D 物理翻转明信片 */
    .postcard-perspective {
      perspective: 1600px;
    }
    
    .postcard-inner {
      position: relative;
      width: 100%;
      height: 100%;
      transition: transform 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      transform-style: preserve-3d;
    }
    
    .postcard-inner.is-flipped {
      transform: rotateY(180deg);
    }
    
    .postcard-front, .postcard-back {
      width: 100%;
      backface-visibility: hidden;
      -webkit-backface-visibility: hidden;
    }
    
    .postcard-back {
      transform: rotateY(180deg);
    }

    /* 复古明信片锯齿/邮票边缘 */
    .stamp-edge {
      background-image: radial-gradient(circle at center, transparent 4px, #FFF9F0 4px);
      background-size: 10px 10px;
    }

    /* 复古盖章动效 */
    @keyframes stampDrop {
      0% {
        opacity: 0;
        transform: scale(3) rotate(-45deg);
        filter: blur(4px);
      }
      70% {
        opacity: 0.9;
        transform: scale(0.9) rotate(-12deg);
        filter: blur(0px);
      }
      85% {
        transform: scale(1.1) rotate(-17deg);
      }
      100% {
        opacity: 0.85;
        transform: scale(1) rotate(-15deg);
      }
    }

    .animate-stamp-drop {
      animation: stampDrop 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
      transform-origin: center;
    }

    /* 物理打印还原样式 */
    @media print {
      body {
        background: white !important;
        color: black !important;
      }
      .no-print {
        display: none !important;
      }
      .print-card {
        border: 2px solid #000 !important;
        box-shadow: none !important;
        page-break-inside: avoid;
        margin-bottom: 2cm !important;
        width: 100% !important;
        max-width: 15cm !important;
        height: 10cm !important;
        display: block !important;
      }
      .postcard-front, .postcard-back {
        position: static !important;
        transform: none !important;
        backface-visibility: visible !important;
        display: block !important;
        page-break-after: always;
      }
    }
  `;
  document.head.appendChild(style);
}
injectTailwindTheme();