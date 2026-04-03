export const FDS_THEME = {
  token: {
    colorPrimary: "#6366f1",
    colorSuccess: "#10B981",
    colorWarning: "#F59E0B",
    colorError: "#EF4444",
    colorInfo: "#3B82F6",
    colorTextBase: "#e2e8f0",
    colorBgBase: "#0f172a",
    colorBgContainer: "#1e293b",
    colorBgElevated: "#1e293b",
    colorBgLayout: "#0f172a",
    borderRadius: 8,
    borderRadiusSM: 6,
    borderRadiusLG: 12,
    borderRadiusXL: 12,
    fontSize: 14,
    fontSizeLG: 16,
    fontSizeHeading3: 24,
    fontSizeHeading4: 20,
    fontSizeHeading5: 18,
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    controlHeight: 36,
    controlHeightSM: 28,
    controlHeightLG: 40,
    colorText: "#e2e8f0",
    colorTextSecondary: "#94a3b8",
    colorTextTertiary: "#64748b",
    colorTextQuaternary: "#475569",
    colorFill: "#1e293b",
    colorFillSecondary: "#334155",
    colorFillTertiary: "#1e293b",
    colorBorder: "#334155",
    colorBorderSecondary: "#1e293b",
    boxShadowTertiary: "0 2px 4px rgba(0,0,0,0.2)",
    boxShadowSecondary:
      "0 4px 6px -1px rgba(0,0,0,0.3)",
    boxShadow: "0 10px 15px rgba(0,0,0,0.2)",
    wireframe: false,
  },
  components: {
    Button: {
      borderRadius: 8,
      borderRadiusSM: 6,
      borderRadiusLG: 8,
      controlHeight: 36,
      controlHeightSM: 28,
      controlHeightLG: 40,
      primaryColor: "#FFFFFF",
      fontWeight: 500,
      paddingInline: 16,
      paddingInlineSM: 12,
      paddingInlineLG: 20,
    },
    Card: {
      borderRadiusLG: 8,
      borderRadiusSM: 8,
      boxShadowTertiary: "0 2px 4px rgba(0,0,0,0.2)",
      paddingLG: 16,
      padding: 16,
      paddingSM: 12,
    },
    Layout: {
      colorBgHeader: "#1e293b",
      colorBgBody: "#0f172a",
      colorBgSider: "#1e293b",
      headerHeight: 56,
      headerPadding: "0 24px",
      siderWidth: 280,
    },
    Menu: {
      colorItemBgSelected: "#334155",
      colorItemTextSelected: "#e2e8f0",
      colorItemText: "#94a3b8",
      colorItemTextHover: "#e2e8f0",
      colorItemBgHover: "#334155",
      itemHeight: 40,
      itemMarginInline: 8,
      borderRadius: 8,
    },
    Input: {
      borderRadius: 8,
      borderRadiusSM: 6,
      borderRadiusLG: 8,
      controlHeight: 36,
      controlHeightSM: 28,
      controlHeightLG: 40,
      paddingInline: 12,
      paddingBlock: 6,
    },
    Select: {
      borderRadius: 8,
      borderRadiusSM: 6,
      borderRadiusLG: 8,
      controlHeight: 36,
      controlHeightSM: 28,
      controlHeightLG: 40,
    },
    Table: {
      headerBg: "#1e293b",
      borderRadiusLG: 8,
      cellPaddingBlock: 12,
      cellPaddingInline: 16,
      headerSplitColor: "transparent",
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
    Radio: {
      colorPrimary: "#6366f1",
    },
  },
};

export const FDS_CSS_VARS = `
  :root {
    --flow-color-primary: #6366f1;
    --flow-color-success: #10B981;
    --flow-color-warning: #F59E0B;
    --flow-color-danger: #EF4444;
    --flow-color-info: #3B82F6;

    --flow-bg-page: #0f172a;
    --flow-bg-card: #1e293b;
    --flow-bg-layer: #1e293b;

    --flow-text-title: #e2e8f0;
    --flow-text-primary: #e2e8f0;
    --flow-text-secondary: #94A3B8;
    --flow-text-disabled: #64748B;

    --flow-border-radius-sm: 6px;
    --flow-border-radius-md: 8px;
    --flow-border-radius-lg: 12px;
    --flow-border-radius-full: 9999px;

    --flow-shadow-light: 0 2px 4px rgba(0,0,0,0.2);
    --flow-shadow-medium: 0 4px 6px -1px rgba(0,0,0,0.3);
    --flow-shadow-heavy: 0 10px 15px rgba(0,0,0,0.2);

    --flow-spacing-xs: 4px;
    --flow-spacing-sm: 8px;
    --flow-spacing-md: 16px;
    --flow-spacing-lg: 24px;
    --flow-spacing-xl: 32px;

    --flow-gradient-autoflow: linear-gradient(135deg, #6366f1 0%, #10B981 100%);
    --flow-gradient-knowflow: linear-gradient(135deg, #6366f1 0%, #7C3AED 100%);
    --flow-gradient-harvestflow: linear-gradient(135deg, #6366f1 0%, #F59E0B 100%);
  }
`;
