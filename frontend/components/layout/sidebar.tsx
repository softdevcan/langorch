"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import {
  Users,
  LayoutDashboard,
  Settings,
  Building2,
  LogOut,
  FileText
} from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import { UserRole } from "@/lib/types";

interface NavItem {
  titleKey: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: UserRole[];
}

const navItems: NavItem[] = [
  {
    titleKey: "dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    titleKey: "documents",
    href: "/dashboard/documents",
    icon: FileText,
  },
  {
    titleKey: "users",
    href: "/dashboard/users",
    icon: Users,
  },
  {
    titleKey: "tenants",
    href: "/dashboard/tenants",
    icon: Building2,
    roles: [UserRole.SUPER_ADMIN],
  },
  {
    titleKey: "settings",
    href: "/dashboard/settings",
    icon: Settings,
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const t = useTranslations("nav");

  const filteredNavItems = navItems.filter((item) => {
    if (!item.roles) return true;
    return user && item.roles.includes(user.role);
  });

  const handleLogout = async () => {
    await logout();
  };

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r bg-background">
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center border-b px-6">
          <Link href="/dashboard" className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-lg">L</span>
            </div>
            <span className="text-xl font-bold">LangOrch</span>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {filteredNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <Icon className="h-5 w-5" />
                {t(item.titleKey as any)}
              </Link>
            );
          })}
        </nav>

        {/* User Profile & Logout */}
        <div className="border-t p-4">
          <div className="mb-3 rounded-lg bg-muted px-3 py-2">
            <p className="text-sm font-medium truncate">{user?.full_name}</p>
            <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Role: <span className="font-medium">{user?.role}</span>
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <LogOut className="h-5 w-5" />
            {t("logout")}
          </button>
        </div>
      </div>
    </aside>
  );
}
