export const AWAITING_SUPPLIER_TAG = "Awaiting Supplier Info (Quotes)";
export const READY_TO_SEND_TAG = "Quotes Ready to send (Quotes)";
export const MUST_ATTEND_TAG = "Must Attend (Quotes)";
export const BOOKED_TAG = "Booked (Quotes)";
export const AWAITING_DESKTOP_INFO_TAG = "Awaiting Desktop Info (Quotes)";
export const AWAITING_INTERNAL_INFO_TAG = "Awaiting Internal Info (Quotes)";

export type DashboardQuoteRow = {
  id: number;
  eworks_quote_id: number;
  quote_ref: string | null;
  customer_name: string | null;
  status: string | null;
  status_name: string | null;
  tags: string[];
  quote_date: string | null;
  expiry_date: string | null;
  total: number | null;
  synced_at: string | null;
};

export type DashboardCategory = {
  count: number;
  filtered_count?: number | null;
  quotes: DashboardQuoteRow[];
};

export type OperationalDashboardData = {
  categories: {
    new_quotes: DashboardCategory;
    awaiting_supplier: DashboardCategory;
    ready_to_send: DashboardCategory;
    booked: DashboardCategory;
    must_attend: DashboardCategory;
    awaiting_desktop_info: DashboardCategory;
    awaiting_internal_info: DashboardCategory;
  };
  last_synced_at: string | null;
  totals: {
    all_open_quotes: number;
  };
};
