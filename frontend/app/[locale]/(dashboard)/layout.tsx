import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { ApprovalPanel } from "@/components/hitl/approval-panel";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col ml-64">
        <Header />
        <main className="flex-1 overflow-y-auto bg-muted/30 p-6">
          {children}
        </main>
      </div>

      {/* HITL Approval Panel (floating) */}
      <ApprovalPanel />
    </div>
  );
}
