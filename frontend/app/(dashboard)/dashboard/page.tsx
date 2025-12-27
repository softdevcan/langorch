"use client";

import { useAuthStore } from "@/stores/auth-store";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, Building2, Activity, TrendingUp } from "lucide-react";

export default function DashboardPage() {
  const { user } = useAuthStore();

  const stats = [
    {
      title: "Total Users",
      value: "0",
      description: "Active users in your tenant",
      icon: Users,
      trend: "+0%",
    },
    {
      title: "Tenants",
      value: "1",
      description: "Total active tenants",
      icon: Building2,
      trend: "+0%",
      showForRole: ["super_admin"],
    },
    {
      title: "API Calls",
      value: "0",
      description: "Last 30 days",
      icon: Activity,
      trend: "+0%",
    },
    {
      title: "Success Rate",
      value: "0%",
      description: "API success rate",
      icon: TrendingUp,
      trend: "+0%",
    },
  ];

  const filteredStats = stats.filter(
    (stat) => !stat.showForRole || (user && stat.showForRole.includes(user.role))
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">
          Welcome back, {user?.full_name?.split(" ")[0] || "User"}!
        </h2>
        <p className="text-muted-foreground">
          Here&apos;s an overview of your LangOrch workspace
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {filteredStats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {stat.title}
                </CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <p className="text-xs text-muted-foreground">
                  {stat.description}
                </p>
                <p className="text-xs text-green-600 mt-1">
                  {stat.trend} from last month
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>
            Get started with common tasks
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border p-4 hover:border-primary transition-colors cursor-pointer">
            <Users className="h-8 w-8 mb-2 text-primary" />
            <h3 className="font-semibold mb-1">Manage Users</h3>
            <p className="text-sm text-muted-foreground">
              Create and manage user accounts
            </p>
          </div>
          <div className="rounded-lg border p-4 hover:border-primary transition-colors cursor-pointer opacity-50">
            <Activity className="h-8 w-8 mb-2 text-muted-foreground" />
            <h3 className="font-semibold mb-1">View Analytics</h3>
            <p className="text-sm text-muted-foreground">
              Coming in Version 0.2
            </p>
          </div>
          <div className="rounded-lg border p-4 hover:border-primary transition-colors cursor-pointer opacity-50">
            <TrendingUp className="h-8 w-8 mb-2 text-muted-foreground" />
            <h3 className="font-semibold mb-1">API Metrics</h3>
            <p className="text-sm text-muted-foreground">
              Coming in Version 0.2
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
