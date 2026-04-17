import { RouterProvider, createBrowserRouter } from "react-router-dom";
import { MainLayout } from "./layouts/MainLayout";
import { LoginPage } from "./pages/Login";
import { DashboardPage } from "./pages/Dashboard";
import { AffectationPage } from "./pages/Affectation";
import { PlanningPage } from "./pages/Planning";
import { PostesPage } from "./pages/Postes";
import { SoignantsPage } from "./pages/Soignants";
import { GeneratorPage } from "./pages/Generator";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AuthProvider } from "./hooks/useAuth";
import "./App.css";

const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "soignants", element: <SoignantsPage /> },
      { path: "postes", element: <PostesPage /> },
      { path: "affectation", element: <AffectationPage /> },
      { path: "planning", element: <PlanningPage /> },
      { path: "generator", element: <GeneratorPage /> },
    ],
  },
]);

function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  );
}

export default App;
