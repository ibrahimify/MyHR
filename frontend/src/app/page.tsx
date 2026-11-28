"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  Award,
  Building2,
  ChevronLeft,
  ChevronRight,
  CircleCheck,
  ClipboardList,
  CloudUpload,
  LayoutDashboard,
  Mail,
  Menu,
  LogOut,
  Network,
  Pencil,
  Phone,
  Plus,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  TrendingUp,
  TriangleAlert,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";
import { EmployeeForm } from "@/components/employee-form";
import { RequireAuth, useAuth } from "@/components/auth-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import {
  ApiError,
  Employee,
  EmployeePage,
  getEmployee,
  listEmployees,
} from "@/lib/employees";

const PAGE_SIZE = 10;
const emptyPage: EmployeePage = {
  items: [],
  total: 0,
  page: 1,
  page_size: PAGE_SIZE,
  pages: 1,
};

const navigationGroups = [
  {
    label: "Overview",
    items: [{ label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    label: "People",
    items: [
      { label: "Employees", icon: UsersRound, active: true },
      { label: "Org hierarchy", icon: Network },
    ],
  },
  {
    label: "Growth",
    items: [
      { label: "Promotions", icon: TrendingUp },
      { label: "Commendations", icon: Award },
    ],
  },
  {
    label: "Compliance",
    items: [
      { label: "Sanctions", icon: TriangleAlert },
      { label: "Audit log", icon: ClipboardList },
      { label: "Anomaly review", icon: Search },
    ],
  },
  {
    label: "Data",
    items: [{ label: "Import data", icon: CloudUpload }],
  },
  {
    label: "System",
    items: [{ label: "Settings", icon: Settings }],
  },
];

export default function Home() {
  return (
    <RequireAuth>
      <EmployeeDirectory />
    </RequireAuth>
  );
}

function EmployeeDirectory() {
  const { user, signOut } = useAuth();
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [employees, setEmployees] = useState(emptyPage);
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selected, setSelected] = useState<Employee | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");
  const [formEmployee, setFormEmployee] = useState<Employee | null | undefined>(
    undefined,
  );
  const [notice, setNotice] = useState("");
  const listRequestSequence = useRef(0);
  const detailRequestSequence = useRef(0);

  const loadEmployees = useCallback(
    (signal?: AbortSignal) => {
      const requestSequence = ++listRequestSequence.current;
      setLoading(true);
      setError("");
      setSelectedId(null);
      setSelected(null);
      setDetailError("");
      return listEmployees({
        search,
        status,
        page,
        pageSize: PAGE_SIZE,
        signal,
      })
        .then((result) => {
          if (requestSequence !== listRequestSequence.current) return;
          setEmployees(result);
          setSelectedId(result.items[0]?.id ?? null);
        })
        .catch((reason) => {
          if (reason instanceof DOMException && reason.name === "AbortError")
            return;
          if (requestSequence !== listRequestSequence.current) return;
          setError(
            reason instanceof ApiError
              ? reason.message
              : reason instanceof Error
                ? reason.message
              : "Employees could not be loaded.",
          );
        })
        .finally(() => {
          if (requestSequence === listRequestSequence.current) {
            setLoading(false);
          }
        });
    },
    [page, search, status],
  );

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void loadEmployees(controller.signal);
    }, 0);
    return () => {
      window.clearTimeout(timer);
      listRequestSequence.current += 1;
      controller.abort();
    };
  }, [loadEmployees]);
  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      const requestSequence = ++detailRequestSequence.current;
      setSelected(null);
      setDetailError("");
      if (selectedId === null) {
        setDetailLoading(false);
        return;
      }
      setDetailLoading(true);
      void getEmployee(selectedId, controller.signal)
        .then((employee) => {
          if (requestSequence === detailRequestSequence.current) {
            setSelected(employee);
          }
        })
        .catch((reason) => {
          if (reason instanceof DOMException && reason.name === "AbortError")
            return;
          if (requestSequence !== detailRequestSequence.current) return;
          setDetailError(
            reason instanceof ApiError
              ? reason.message
              : "Employee details could not be loaded.",
          );
        })
        .finally(() => {
          if (requestSequence === detailRequestSequence.current) {
            setDetailLoading(false);
          }
        });
    }, 0);
    return () => {
      window.clearTimeout(timer);
      detailRequestSequence.current += 1;
      controller.abort();
    };
  }, [selectedId]);
  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 4500);
    return () => window.clearTimeout(timer);
  }, [notice]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-heading">
          <a className="brand" href="#main" aria-label="MyHR employees">
            <span className="brand-mark">
              <Building2 size={21} />
            </span>
            <span>
              <b>MyHR.</b>
              <small>Employee Management</small>
            </span>
          </a>
          <button
            className="mobile-menu-button"
            onClick={() => setNavigationOpen((open) => !open)}
            aria-expanded={navigationOpen}
            aria-label={navigationOpen ? "Close navigation" : "Open navigation"}
            type="button"
          >
            {navigationOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
        <div className={`sidebar-body ${navigationOpen ? "open" : ""}`}>
          <nav aria-label="Main navigation">
            {navigationGroups.map((group) => (
              <div className="nav-group" key={group.label}>
                <div className="nav-section-heading">
                  <span>{group.label}</span>
                  <i />
                </div>
                {group.items.map((item) => {
                  const Icon = item.icon;
                  return item.active ? (
                    <a
                      className="nav-item active"
                      href="#employees"
                      key={item.label}
                      onClick={() => setNavigationOpen(false)}
                    >
                      <Icon size={18} />
                      <span>{item.label}</span>
                    </a>
                  ) : (
                    <button
                      className="nav-item"
                      key={item.label}
                      onClick={() => {
                        setNotice(`${item.label} will be added in a later milestone.`);
                        setNavigationOpen(false);
                      }}
                      title={`${item.label} is not yet available on the web`}
                      type="button"
                    >
                      <Icon size={18} />
                      <span>{item.label}</span>
                    </button>
                  );
                })}
              </div>
            ))}
          </nav>
          <div className="sidebar-footer">
            <div className="identity-card">
              <span className="avatar">{initials(user?.email ?? "Local operator")}</span>
              <span>
                <b>{user?.email?.split("@")[0] ?? "Local operator"}</b>
                <small>{user ? "Administrator" : "Local development"}</small>
              </span>
            </div>
            <ThemeToggle />
            {user && (
              <button
                className="logout-button"
                onClick={() => void signOut()}
                type="button"
              >
                <LogOut size={17} />
                Sign out
              </button>
            )}
          </div>
        </div>
      </aside>
      <main className="workspace" id="main">
        <header className="page-header">
          <div>
            <p className="breadcrumb">People <ChevronRight size={13} /> Employees</p>
            <h1 id="employees">Employees</h1>
            <p>Manage employee records, assignments, and work details.</p>
          </div>
          <div className="header-actions">
            <div
              className="environment-badge"
              title="Your organization is resolved from the signed-in account"
            >
              <ShieldCheck size={16} />
              {user ? "Secure workspace" : "Local development"}
            </div>
            <button
              className="button button-primary"
              type="button"
              onClick={() => setFormEmployee(null)}
            >
              <Plus size={17} />
              Add employee
            </button>
          </div>
        </header>
        <section className="directory-panel" aria-label="Employee directory">
          <div className="panel-heading">
            <div>
              <span className="panel-icon"><UsersRound size={18} /></span>
              <div>
                <h2>Employee directory</h2>
                <p>Search the organization and inspect one record at a time.</p>
              </div>
            </div>
            <span className="record-count">
              {loading ? "Loading" : `${employees.total} records`}
            </span>
          </div>
          <div className="toolbar">
            <form
              className="search-control"
              role="search"
              onSubmit={(event) => {
                event.preventDefault();
                setPage(1);
                setSearch(searchDraft.trim());
              }}
            >
              <Search size={17} aria-hidden="true" />
              <input
                aria-label="Search employees"
                onChange={(event) => setSearchDraft(event.target.value)}
                placeholder="Search name, ID or position"
                value={searchDraft}
              />
              <button type="submit">Search</button>
            </form>
            <label className="filter-control">
              <span>Status</span>
              <select
                value={status}
                onChange={(event) => {
                  setStatus(event.target.value);
                  setPage(1);
                }}
              >
                <option value="">All statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="on_leave">On leave</option>
                <option value="terminated">Terminated</option>
              </select>
            </label>
          </div>
          <div className="directory-layout">
            <section
              className="list-region"
              aria-busy={loading}
              aria-label="Employees"
            >
              <div className="section-heading">
                <div>
                  <h3>Directory</h3>
                  <p>
                    {loading
                      ? "Loading records"
                      : `${employees.total} employee${employees.total === 1 ? "" : "s"}`}
                  </p>
                </div>
                <button
                  className="icon-button"
                  onClick={() => loadEmployees()}
                  aria-label="Refresh employees"
                  title="Refresh employees"
                >
                  <RefreshCw size={17} />
                </button>
              </div>
              {loading && <ListSkeleton />}
              {!loading && error && (
                <StateMessage
                  kind="error"
                  title="Directory unavailable"
                  message={error}
                  action={() => loadEmployees()}
                />
              )}
              {!loading && !error && !employees.items.length && (
                <StateMessage
                  kind="empty"
                  title={
                    search || status
                      ? "No matching employees"
                      : "No employees yet"
                  }
                  message={
                    search || status
                      ? "Adjust the search or status filter."
                      : "Add the first employee to this organization."
                  }
                  action={
                    search || status
                      ? () => {
                          setSearchDraft("");
                          setSearch("");
                          setStatus("");
                          setPage(1);
                        }
                      : () => setFormEmployee(null)
                  }
                  actionLabel={
                    search || status ? "Clear filters" : "Add employee"
                  }
                />
              )}
              {!loading && !error && !!employees.items.length && (
                <div className="employee-list">
                  {employees.items.map((employee) => (
                    <button
                      className={`employee-row ${selectedId === employee.id ? "selected" : ""}`}
                      key={employee.id}
                      onClick={() => setSelectedId(employee.id)}
                      type="button"
                    >
                      <span className="employee-initials">
                        {initials(employee.full_name)}
                      </span>
                      <span className="employee-summary">
                        <span>
                          <b>{employee.full_name}</b>
                          <StatusBadge status={employee.status} />
                        </span>
                        <small>
                          {employee.employee_id} ·{" "}
                          {employee.position || "Position not set"}
                        </small>
                      </span>
                      <ChevronRight size={17} aria-hidden="true" />
                    </button>
                  ))}
                </div>
              )}
              {!loading && !error && employees.total > 0 && (
                <footer className="pagination">
                  <span>
                    Page {employees.page} of {employees.pages}
                  </span>
                  <div>
                    <button
                      className="icon-button"
                      disabled={page <= 1}
                      onClick={() => setPage((value) => value - 1)}
                      aria-label="Previous page"
                    >
                      <ChevronLeft size={17} />
                    </button>
                    <button
                      className="icon-button"
                      disabled={page >= employees.pages}
                      onClick={() => setPage((value) => value + 1)}
                      aria-label="Next page"
                    >
                      <ChevronRight size={17} />
                    </button>
                  </div>
                </footer>
              )}
            </section>
            <section
              className="detail-region"
              aria-busy={detailLoading}
              aria-live="polite"
            >
              {detailLoading && <DetailSkeleton />}
              {!detailLoading && detailError && (
                <StateMessage
                  kind="error"
                  title="Record unavailable"
                  message={detailError}
                />
              )}
              {!detailLoading && !detailError && !selected && (
                <StateMessage
                  kind="empty"
                  title="Select an employee"
                  message="Choose a record from the directory to inspect its work details."
                />
              )}
              {!detailLoading && !detailError && selected && (
                <EmployeeDetail
                  employee={selected}
                  onEdit={() => setFormEmployee(selected)}
                />
              )}
            </section>
          </div>
        </section>
        <footer className="page-footer">
          <ShieldCheck size={13} />
          Organization access is resolved from your verified account.
        </footer>
      </main>
      {formEmployee !== undefined && (
        <EmployeeForm
          employee={formEmployee}
          onClose={() => setFormEmployee(undefined)}
          onSaved={(employee, created) => {
            setFormEmployee(undefined);
            setNotice(
              created
                ? `${employee.full_name} was added.`
                : `${employee.full_name} was updated.`,
            );
            setSelectedId(employee.id);
            setSelected(employee);
            loadEmployees();
          }}
        />
      )}
      {notice && (
        <div className="toast" role="status">
          <CircleCheck size={18} />
          {notice}
        </div>
      )}
    </div>
  );
}

function EmployeeDetail({
  employee,
  onEdit,
}: {
  employee: Employee;
  onEdit: () => void;
}) {
  return (
    <article className="employee-detail">
      <header className="profile-header">
        <span className="profile-avatar">{initials(employee.full_name)}</span>
        <div>
          <p>{employee.employee_id}</p>
          <h2>{employee.full_name}</h2>
          <span>{employee.position}</span>
        </div>
        <button
          className="button button-secondary"
          onClick={onEdit}
          type="button"
        >
          <Pencil size={16} />
          Edit
        </button>
      </header>
      <div className="profile-facts">
        <Fact label="Status">
          <StatusBadge status={employee.status} />
        </Fact>
        <Fact label="Joined">{formatDate(employee.join_date)}</Fact>
        <Fact label="Title">
          {employee.title_name || `Title #${employee.title_id}`}
        </Fact>
        <Fact label="Organization unit">
          {employee.org_unit_name ||
            (employee.org_unit_id
              ? `Unit #${employee.org_unit_id}`
              : "Not assigned")}
        </Fact>
        <Fact label="Manager">
          {employee.reports_to_name ||
            (employee.reports_to_id
              ? `Employee #${employee.reports_to_id}`
              : "Not assigned")}
        </Fact>
        <Fact label="Base salary">
          {formatCurrency(employee.base_salary, employee.title_currency)}
        </Fact>
      </div>
      <section className="contact-section">
        <h3>Work contact</h3>
        <div>
          <span>
            <Mail size={16} />
            {employee.work_email || "No work email"}
          </span>
          <span>
            <Phone size={16} />
            {employee.work_phone || "No work phone"}
          </span>
        </div>
      </section>
    </article>
  );
}

function Fact({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="fact">
      <span>{label}</span>
      <div>{children}</div>
    </div>
  );
}
function StatusBadge({ status }: { status: Employee["status"] }) {
  return (
    <span className={`status status-${status}`}>
      {status.replace("_", " ")}
    </span>
  );
}
function StateMessage({
  kind,
  title,
  message,
  action,
  actionLabel = "Try again",
}: {
  kind: "empty" | "error";
  title: string;
  message: string;
  action?: () => void;
  actionLabel?: string;
}) {
  const Icon = kind === "error" ? AlertCircle : UserRound;
  return (
    <div className={`state-message ${kind}`}>
      <Icon size={25} />
      <h3>{title}</h3>
      <p>{message}</p>
      {action && (
        <button
          className="button button-secondary"
          onClick={action}
          type="button"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
function ListSkeleton() {
  return (
    <div className="skeleton-list" aria-label="Loading employees">
      {[1, 2, 3, 4, 5].map((item) => (
        <div key={item}>
          <i />
          <span>
            <b />
            <small />
          </span>
        </div>
      ))}
    </div>
  );
}
function DetailSkeleton() {
  return (
    <div className="detail-skeleton" aria-label="Loading employee details">
      <i />
      <b />
      <span />
      <div>
        {[1, 2, 3, 4, 5, 6].map((item) => (
          <small key={item} />
        ))}
      </div>
    </div>
  );
}
function initials(name: string) {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "--"
  );
}
function formatDate(value?: string) {
  if (!value) return "Not recorded";
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? value
    : new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(date);
}
function formatCurrency(value?: number, currency?: string) {
  return value === undefined
    ? "Not recorded"
    : currency
      ? new Intl.NumberFormat("en", {
          style: "currency",
          currency,
          maximumFractionDigits: 0,
        }).format(value)
      : new Intl.NumberFormat("en", { maximumFractionDigits: 0 }).format(value);
}
