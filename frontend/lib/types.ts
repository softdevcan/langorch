// User & Auth Types
export enum UserRole {
  SUPER_ADMIN = "super_admin",
  TENANT_ADMIN = "tenant_admin",
  USER = "user",
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  tenant_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface UserCreate {
  email: string;
  password: string;
  full_name: string;
  role: UserRole;
  tenant_id?: string;
}

export interface UserUpdate {
  email?: string;
  full_name?: string;
  role?: UserRole;
  is_active?: boolean;
  password?: string;
}

// Tenant Types
export interface Tenant {
  id: string;
  name: string;
  slug: string;
  settings: Record<string, any>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// API Response Types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}
