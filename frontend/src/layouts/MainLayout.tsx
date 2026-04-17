import { Outlet } from "react-router-dom";
import { Sidebar } from "../components/Sidebar";
import { UserMenu } from "../components/UserMenu";
import { useAuth } from "../hooks/useAuth";

export function MainLayout() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="appShell">
      <Sidebar />
      <main className="appMain">
        <div style={{
          display: "flex",
          justifyContent: "flex-end",
          padding: "12px 24px",
          borderBottom: "1px solid rgba(255,255,255,0.05)",
          background: "rgba(0,0,0,0.2)",
        }}>
          {isAuthenticated ? (
            <UserMenu />
          ) : null}
        </div>
        <div style={{ padding: 24 }}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
