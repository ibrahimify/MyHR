import { createBrowserRouter } from "react-router";
import { Login } from "./pages/Login";
import { MainLayout } from "./layouts/MainLayout";
import { Dashboard } from "./pages/Dashboard";
import { EmployeeList } from "./pages/EmployeeList";
import { EmployeeProfile } from "./pages/EmployeeProfile";
import { AddEmployee } from "./pages/AddEmployee";
import { ImportData } from "./pages/ImportData";
import { OrgHierarchy } from "./pages/OrgHierarchy";
import { PromotionManagement } from "./pages/PromotionManagement";
import { Commendation } from "./pages/Commendation";
import { Sanctions } from "./pages/Sanctions";
import { AuditLog } from "./pages/AuditLog";
import { Settings } from "./pages/Settings";

export const router = createBrowserRouter([
  {
    path: "/login",
    Component: Login,
  },
  {
    path: "/",
    Component: MainLayout,
    children: [
      { index: true, Component: Dashboard },
      { path: "employees", Component: EmployeeList },
      { path: "employees/:id", Component: EmployeeProfile },
      { path: "employees/new", Component: AddEmployee },
      { path: "import", Component: ImportData },
      { path: "hierarchy", Component: OrgHierarchy },
      { path: "promotions", Component: PromotionManagement },
      { path: "commendations", Component: Commendation },
      { path: "sanctions", Component: Sanctions },
      { path: "audit", Component: AuditLog },
      { path: "settings", Component: Settings },
    ],
  },
]);
