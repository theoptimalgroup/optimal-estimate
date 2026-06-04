export type UserRole = "admin" | "estimator" | "manager" | "engineer" | "client";

export type CurrentUser = {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  auth_provider?: string;
};
