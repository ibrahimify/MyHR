const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"
)
  .trim()
  .replace(/\/$/, "");

export type EmployeeStatus = "active" | "inactive" | "on_leave" | "terminated";
export type Degree = "BSc" | "MSc" | "PhD" | "Other";

type EmployeeWire = {
  id: number;
  employee_id: string;
  first_name: string;
  last_name: string;
  position: string;
  status: EmployeeStatus;
  title_id: number;
  org_unit_id: number | null;
  organization_id?: number;
  work_email?: string | null;
  work_phone?: string | null;
  join_date?: string;
  base_salary?: number;
  profile_picture?: string | null;
  linkedin_url?: string | null;
  reports_to_id?: number | null;
  created_at?: string;
  updated_at?: string;
  date_of_birth?: string | null;
  phone?: string | null;
  personal_email?: string | null;
  address?: string | null;
  degree?: Degree;
};

export type Employee = EmployeeWire & {
  full_name: string;
  title_name?: string;
  title_currency?: string;
  org_unit_name?: string;
  reports_to_name?: string;
};

export type EmployeePage = {
  items: Employee[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type EmployeeInput = {
  first_name: string;
  last_name: string;
  degree: Degree;
  position: string;
  join_date: string;
  base_salary: number;
  status: EmployeeStatus;
  title_id: number;
  work_email?: string | null;
  work_phone?: string | null;
  org_unit_id?: number | null;
  reports_to_id?: number | null;
};

export type EmployeeOption = { id: number; label: string };
export type EmployeeOptions = {
  titles: EmployeeOption[];
  org_units: EmployeeOption[];
  managers: EmployeeOption[];
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

function normalize(employee: EmployeeWire): Employee {
  return {
    ...employee,
    full_name: `${employee.first_name} ${employee.last_name}`.trim(),
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    let message = `Request failed with status ${response.status}.`;
    try {
      const body = (await response.json()) as {
        detail?: string | Array<{ msg?: string }>;
      };
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail))
        message =
          body.detail
            .map((item) => item.msg)
            .filter(Boolean)
            .join(" ") || message;
    } catch {
      // Keep the status-based message when the response has no JSON body.
    }
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}

export async function listEmployees(options: {
  search?: string;
  status?: string;
  page: number;
  pageSize: number;
  signal?: AbortSignal;
}): Promise<EmployeePage> {
  const params = new URLSearchParams({
    page: String(options.page),
    page_size: String(options.pageSize),
  });
  if (options.search) params.set("search", options.search);
  if (options.status) params.set("status", options.status);
  const result = await request<
    Omit<EmployeePage, "pages" | "items"> & { items: EmployeeWire[] }
  >(`/api/employees?${params}`, { signal: options.signal });
  return {
    ...result,
    items: result.items.map(normalize),
    pages: Math.max(1, Math.ceil(result.total / result.page_size)),
  };
}

export async function getEmployee(
  id: number,
  signal?: AbortSignal,
): Promise<Employee> {
  return normalize(
    await request<EmployeeWire>(`/api/employees/${id}`, { signal }),
  );
}

export async function getEmployeeOptions(
  signal?: AbortSignal,
): Promise<EmployeeOptions> {
  return request<EmployeeOptions>("/api/employees/options", { signal });
}

export async function createEmployee(input: EmployeeInput): Promise<Employee> {
  return normalize(
    await request<EmployeeWire>("/api/employees", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  );
}

export async function updateEmployee(
  id: number,
  input: Partial<EmployeeInput>,
): Promise<Employee> {
  return normalize(
    await request<EmployeeWire>(`/api/employees/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),
  );
}
