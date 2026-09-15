import type { ThemeConfig } from 'ant-design-vue/es/config-provider/context'

export const FDS_THEME: ThemeConfig = {
  token: {
    colorPrimary: '#2563EB',
    colorSuccess: '#10B981',
    colorWarning: '#F59E0B',
    colorError: '#EF4444',
    colorInfo: '#3B82F6',
    colorTextBase: '#1E293B',
    colorBgBase: '#FFFFFF',
    colorBgContainer: '#FFFFFF',
    colorBgElevated: '#FFFFFF',
    colorBgLayout: '#F8FAFC',
    borderRadius: 8,
    borderRadiusSM: 6,
    borderRadiusLG: 12,
    fontSize: 14,
    fontSizeLG: 16,
    fontSizeHeading3: 24,
    fontSizeHeading4: 20,
    fontSizeHeading5: 16,
    fontFamily: "Inter, 'PingFang SC', 'Microsoft YaHei', sans-serif",
    controlHeight: 38,
    controlHeightSM: 30,
    controlHeightLG: 46,
    colorText: '#334155',
    colorTextSecondary: '#64748B',
    colorTextTertiary: '#94A3B8',
    colorTextQuaternary: '#CBD5E1',
    colorFill: '#F1F5F9',
    colorFillSecondary: '#E2E8F0',
    colorFillTertiary: '#F8FAFC',
    colorBorder: '#E2E8F0',
    colorBorderSecondary: '#F1F5F9',
    boxShadowTertiary: '0 1px 2px rgba(15, 23, 42, 0.04)',
    boxShadowSecondary: '0 4px 12px rgba(15, 23, 42, 0.06)',
    boxShadow: '0 8px 24px rgba(15, 23, 42, 0.08)',
    wireframe: false,
  },
  components: {
    Layout: {
      colorBgHeader: '#FFFFFF',
      colorBgBody: '#F8FAFC',
      colorBgTrigger: '#FFFFFF',
    },
    Menu: {
      colorItemBg: 'transparent',
      colorSubItemBg: 'transparent',
      colorItemBgHover: '#F1F5F9',
      colorItemBgActive: '#E2E8F0',
      colorItemBgSelected: '#EFF6FF',
      colorItemText: '#475569',
      colorItemTextHover: '#1D4ED8',
      colorItemTextSelected: '#1D4ED8',
      colorItemTextDisabled: '#CBD5E1',
      colorGroupTitle: '#94A3B8',
      radiusItem: 8,
      radiusSubMenuItem: 8,
      itemMarginInline: 10,
      colorActiveBarWidth: 0,
      colorActiveBarHeight: 0,
      colorActiveBarBorderSize: 0,
    },
    Button: {
      borderRadius: 8,
      borderRadiusSM: 6,
      borderRadiusLG: 10,
      controlHeight: 38,
      controlHeightSM: 30,
      controlHeightLG: 46,
    },
    Card: {
      borderRadiusLG: 12,
      paddingLG: 24,
    },
    Input: {
      borderRadius: 8,
      borderRadiusSM: 6,
      borderRadiusLG: 10,
      controlHeight: 38,
      controlHeightSM: 30,
      controlHeightLG: 46,
    },
    Select: {
      borderRadius: 8,
      borderRadiusSM: 6,
      borderRadiusLG: 10,
      controlHeight: 38,
      controlHeightSM: 30,
      controlHeightLG: 46,
    },
    Table: {
      borderRadiusLG: 12,
    },
    Tag: {
      borderRadiusSM: 9999,
      borderRadius: 9999,
    },
    Alert: {
      borderRadiusLG: 8,
    },
    Dropdown: {
      borderRadiusLG: 8,
    },
    Popover: {
      borderRadiusLG: 8,
    },
    Modal: {
      borderRadiusLG: 12,
    },
    Drawer: {
      borderRadiusLG: 0,
    },
    Avatar: {
      borderRadius: 9999,
    },
    Badge: {
      borderRadiusSM: 9999,
    },
    Progress: {
      borderRadius: 9999,
    },
    Switch: {
      borderRadius: 9999,
    },
  },
}

export const FDS_CSS_VARS = `
  :root {
    --flow-color-primary: #2563EB;
    --flow-color-primary-hover: #1D4ED8;
    --flow-color-primary-soft: #EFF6FF;
    --flow-color-success: #10B981;
    --flow-color-success-soft: #ECFDF5;
    --flow-color-warning: #F59E0B;
    --flow-color-warning-soft: #FFFBEB;
    --flow-color-danger: #EF4444;
    --flow-color-danger-soft: #FEF2F2;
    --flow-color-info: #3B82F6;
    --flow-color-info-soft: #EFF6FF;

    --flow-bg-page: #F8FAFC;
    --flow-bg-card: #FFFFFF;
    --flow-bg-layer: #F1F5F9;
    --flow-bg-sider: #FFFFFF;

    --flow-border-color: #E2E8F0;
    --flow-border-color-soft: #F1F5F9;

    --flow-text-title: #0F172A;
    --flow-text-primary: #334155;
    --flow-text-secondary: #64748B;
    --flow-text-disabled: #94A3B8;

    --flow-border-radius-sm: 6px;
    --flow-border-radius-md: 8px;
    --flow-border-radius-lg: 12px;
    --flow-border-radius-full: 9999px;

    --flow-shadow-light: 0 1px 2px rgba(15, 23, 42, 0.04);
    --flow-shadow-medium: 0 4px 12px rgba(15, 23, 42, 0.06);
    --flow-shadow-heavy: 0 8px 24px rgba(15, 23, 42, 0.08);

    --flow-spacing-xs: 8px;
    --flow-spacing-sm: 16px;
    --flow-spacing-md: 24px;
    --flow-spacing-lg: 32px;
    --flow-spacing-xl: 48px;

    --flow-header-height: 60px;
    --flow-sider-width: 232px;
    --flow-content-max-width: 1280px;

    --flow-font-mono: 'JetBrains Mono', 'Fira Code', 'Monaco', 'Menlo', 'Consolas', monospace;
  }

  html, body {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  .af-page {
    max-width: var(--flow-content-max-width);
    margin: 0 auto;
  }

  .af-section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0 0 16px;
    font-size: 16px;
    font-weight: 600;
    color: var(--flow-text-title);
  }

  .af-section-title .anticon {
    color: var(--flow-color-primary);
  }

  .af-mono {
    font-family: var(--flow-font-mono);
  }

  ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  ::-webkit-scrollbar-thumb {
    background: #CBD5E1;
    border-radius: 9999px;
  }

  ::-webkit-scrollbar-thumb:hover {
    background: #94A3B8;
  }

  ::-webkit-scrollbar-track {
    background: transparent;
  }
`
