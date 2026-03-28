import type { ThemeConfig } from 'ant-design-vue/es/config-provider/context'

export const FDS_THEME: ThemeConfig = {
  token: {
    colorPrimary: '#2563EB',
    colorSuccess: '#10B981',
    colorWarning: '#F59E0B',
    colorError: '#EF4444',
    colorInfo: '#3B82F6',
    colorTextBase: '#334155',
    colorBgBase: '#FFFFFF',
    colorBgContainer: '#FFFFFF',
    colorBgElevated: '#FFFFFF',
    colorBgLayout: '#F8FAFC',
    borderRadius: 6,
    borderRadiusSM: 6,
    borderRadiusLG: 12,
    borderRadiusXL: 12,
    fontSize: 14,
    fontSizeLG: 16,
    fontSizeHeading3: 24,
    fontSizeHeading4: 20,
    fontSizeHeading5: 18,
    fontFamily: 'Inter, PingFang SC, Microsoft YaHei, sans-serif',
    controlHeight: 40,
    controlHeightSM: 32,
    controlHeightLG: 48,
    colorText: '#334155',
    colorTextSecondary: '#64748B',
    colorTextTertiary: '#94A3B8',
    colorTextQuaternary: '#CBD5E1',
    colorFill: '#F1F5F9',
    colorFillSecondary: '#E2E8F0',
    colorFillTertiary: '#F8FAFC',
    colorBorder: '#E2E8F0',
    colorBorderSecondary: '#F1F5F9',
    boxShadowTertiary: '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04)',
    boxShadowSecondary: '0 4px 6px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04)',
    boxShadow: '0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05)',
    wireframe: false,
  },
  components: {
    Button: {
      borderRadius: 6,
      borderRadiusSM: 6,
      borderRadiusLG: 6,
      controlHeight: 40,
      controlHeightSM: 32,
      controlHeightLG: 48,
      primaryColor: '#FFFFFF',
      fontWeight: 500,
      paddingInline: 16,
      paddingInlineSM: 12,
      paddingInlineLG: 20,
    },
    Card: {
      borderRadiusLG: 12,
      borderRadiusSM: 12,
      boxShadowTertiary: '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04)',
      paddingLG: 24,
      padding: 24,
      paddingSM: 16,
    },
    Layout: {
      colorBgHeader: '#FFFFFF',
      colorBgBody: '#F8FAFC',
      colorBgSider: '#1E293B',
      headerHeight: 64,
      headerPadding: '0 24px',
      siderWidth: 240,
    },
    Menu: {
      colorItemBgSelected: '#2563EB',
      colorItemTextSelected: '#FFFFFF',
      colorItemText: '#94A3B8',
      colorItemTextHover: '#FFFFFF',
      colorItemBgHover: '#334155',
      itemHeight: 48,
      itemMarginInline: 8,
      borderRadius: 6,
    },
    Input: {
      borderRadius: 6,
      borderRadiusSM: 6,
      borderRadiusLG: 6,
      controlHeight: 40,
      controlHeightSM: 32,
      controlHeightLG: 48,
      paddingInline: 12,
      paddingBlock: 8,
    },
    Select: {
      borderRadius: 6,
      borderRadiusSM: 6,
      borderRadiusLG: 6,
      controlHeight: 40,
      controlHeightSM: 32,
      controlHeightLG: 48,
    },
    Table: {
      headerBg: '#F8FAFC',
      borderRadiusLG: 12,
      cellPaddingBlock: 16,
      cellPaddingInline: 16,
      headerSplitColor: 'transparent',
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
    --flow-color-success: #10B981;
    --flow-color-warning: #F59E0B;
    --flow-color-danger: #EF4444;
    --flow-color-info: #3B82F6;

    --flow-bg-page: #F8FAFC;
    --flow-bg-card: #FFFFFF;
    --flow-bg-layer: #F1F5F9;

    --flow-text-title: #0F172A;
    --flow-text-primary: #334155;
    --flow-text-secondary: #64748B;
    --flow-text-disabled: #94A3B8;

    --flow-border-radius-sm: 6px;
    --flow-border-radius-md: 8px;
    --flow-border-radius-lg: 12px;
    --flow-border-radius-full: 9999px;

    --flow-shadow-light: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04);
    --flow-shadow-medium: 0 4px 6px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);
    --flow-shadow-heavy: 0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05);

    --flow-spacing-xs: 8px;
    --flow-spacing-sm: 16px;
    --flow-spacing-md: 24px;
    --flow-spacing-lg: 32px;
    --flow-spacing-xl: 48px;

    --flow-gradient-autoflow: linear-gradient(135deg, #2563EB 0%, #10B981 100%);
    --flow-gradient-knowflow: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%);
    --flow-gradient-harvestflow: linear-gradient(135deg, #2563EB 0%, #F59E0B 100%);
  }
`
