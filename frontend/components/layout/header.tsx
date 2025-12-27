"use client";

import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { Bell, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { LanguageSwitcher } from "@/components/language/language-switcher";

const getPageTitleKey = (pathname: string): string => {
  if (pathname === "/dashboard") return "dashboard";
  if (pathname.includes("/users")) return "users";
  if (pathname.includes("/tenants")) return "tenants";
  if (pathname.includes("/documents")) return "documents";
  if (pathname.includes("/settings")) return "settings";
  return "dashboard";
};

export function Header() {
  const pathname = usePathname();
  const t = useTranslations("nav");
  const tCommon = useTranslations("common");
  const pageTitleKey = getPageTitleKey(pathname);

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b bg-background px-6">
      <div className="flex-1">
        <h1 className="text-xl font-semibold">{t(pageTitleKey as any)}</h1>
      </div>

      <div className="flex items-center gap-4">
        {/* Search */}
        <div className="relative hidden md:block">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            placeholder={`${tCommon("search")}...`}
            className="w-64 pl-10"
          />
        </div>

        {/* Language Switcher */}
        <LanguageSwitcher />

        {/* Theme Toggle */}
        <ThemeToggle />

        {/* Notifications */}
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-red-500" />
        </Button>
      </div>
    </header>
  );
}
