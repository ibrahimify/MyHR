"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { LoaderCircle, X } from "lucide-react";
import {
  ApiError,
  createEmployee,
  Degree,
  Employee,
  EmployeeInput,
  EmployeeOptions,
  EmployeeStatus,
  getEmployeeOptions,
  updateEmployee,
} from "@/lib/employees";

type Props = {
  employee: Employee | null;
  onClose: () => void;
  onSaved: (employee: Employee, created: boolean) => void;
};

const statuses: Array<{ value: EmployeeStatus; label: string }> = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "on_leave", label: "On leave" },
  { value: "terminated", label: "Terminated" },
];

export function EmployeeForm({ employee, onClose, onSaved }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [options, setOptions] = useState<EmployeeOptions | null>(null);
  const [optionsError, setOptionsError] = useState("");

  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      );
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    panelRef.current?.querySelector<HTMLElement>("input, select, button")?.focus();
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  }, [onClose]);

  useEffect(() => {
    const controller = new AbortController();
    getEmployeeOptions(controller.signal)
      .then(setOptions)
      .catch((reason) => {
        if (reason instanceof DOMException && reason.name === "AbortError")
          return;
        setOptionsError(
          reason instanceof ApiError
            ? reason.message
            : "Reference choices could not be loaded.",
        );
      });
    return () => controller.abort();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const optionalNumber = (name: string) => {
      const value = String(data.get(name) ?? "").trim();
      return value ? Number(value) : null;
    };
    const input: EmployeeInput = {
      first_name: String(data.get("first_name") ?? "").trim(),
      last_name: String(data.get("last_name") ?? "").trim(),
      degree: String(data.get("degree")) as Degree,
      position: String(data.get("position") ?? "").trim(),
      join_date: String(data.get("join_date")),
      base_salary: Number(data.get("base_salary")),
      status: String(data.get("status")) as EmployeeStatus,
      title_id: Number(data.get("title_id")),
      work_email: String(data.get("work_email") ?? "").trim() || null,
      work_phone: String(data.get("work_phone") ?? "").trim() || null,
      org_unit_id: optionalNumber("org_unit_id"),
      reports_to_id: optionalNumber("reports_to_id"),
    };
    try {
      const saved = employee
        ? await updateEmployee(employee.id, input)
        : await createEmployee(input);
      onSaved(saved, !employee);
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "The employee could not be saved.",
      );
      setSaving(false);
    }
  }

  const joined = employee?.join_date?.slice(0, 10) ?? "";
  return (
    <div
      className="dialog-backdrop"
      role="presentation"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <div
        className="dialog-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="employee-form-title"
        tabIndex={-1}
        ref={panelRef}
      >
        <header className="dialog-header">
          <div>
            <p className="eyebrow">Employee record</p>
            <h2 id="employee-form-title">
              {employee ? "Edit employee" : "Add employee"}
            </h2>
            <p>Required fields are marked with an asterisk.</p>
          </div>
          <button
            className="icon-button"
            type="button"
            onClick={onClose}
            aria-label="Close form"
          >
            <X size={18} />
          </button>
        </header>
        <form className="employee-form" onSubmit={submit}>
          {(error || optionsError) && (
            <div className="form-alert" role="alert">
              {error || optionsError}
            </div>
          )}
          <fieldset>
            <legend>Identity</legend>
            <div className="form-grid">
              <Field
                label="First name"
                name="first_name"
                required
                defaultValue={employee?.first_name}
              />
              <Field
                label="Last name"
                name="last_name"
                required
                defaultValue={employee?.last_name}
              />
              <label className="field">
                <span>
                  Degree <b>*</b>
                </span>
                <select
                  name="degree"
                  required
                  defaultValue={employee?.degree ?? "BSc"}
                >
                  {(["BSc", "MSc", "PhD", "Other"] as Degree[]).map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
                <small />
              </label>
            </div>
          </fieldset>
          <fieldset>
            <legend>Employment</legend>
            <div className="form-grid">
              <Field
                label="Position"
                name="position"
                required
                defaultValue={employee?.position}
              />
              <Field
                label="Join date"
                name="join_date"
                type="date"
                required
                defaultValue={joined}
              />
              <Field
                label="Base salary"
                name="base_salary"
                type="number"
                min="0"
                step="0.01"
                required
                defaultValue={employee?.base_salary}
              />
              <label className="field">
                <span>
                  Status <b>*</b>
                </span>
                <select
                  name="status"
                  required
                  defaultValue={employee?.status ?? "active"}
                >
                  {statuses.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
                <small />
              </label>
              <OptionField
                label="Title"
                name="title_id"
                required
                defaultValue={employee?.title_id}
                options={options?.titles ?? []}
                loading={!options && !optionsError}
              />
              <OptionField
                label="Organization unit"
                name="org_unit_id"
                defaultValue={employee?.org_unit_id ?? undefined}
                options={options?.org_units ?? []}
                loading={!options && !optionsError}
                emptyLabel="Not assigned"
              />
              <OptionField
                label="Manager"
                name="reports_to_id"
                defaultValue={employee?.reports_to_id ?? undefined}
                options={(options?.managers ?? []).filter(
                  (item) => item.id !== employee?.id,
                )}
                loading={!options && !optionsError}
                emptyLabel="Not assigned"
              />
            </div>
          </fieldset>
          <fieldset>
            <legend>Work contact</legend>
            <div className="form-grid">
              <Field
                label="Work email"
                name="work_email"
                type="email"
                defaultValue={employee?.work_email ?? undefined}
              />
              <Field
                label="Work phone"
                name="work_phone"
                defaultValue={employee?.work_phone ?? undefined}
              />
            </div>
          </fieldset>
          <div className="dialog-actions">
            <button
              className="button button-secondary"
              type="button"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              className="button button-primary"
              disabled={saving}
              type="submit"
            >
              {saving && <LoaderCircle className="spin" size={17} />}
              {saving ? "Saving" : employee ? "Save changes" : "Add employee"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({
  label,
  hint = "",
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>
        {label} {props.required && <b>*</b>}
      </span>
      <input {...props} />
      <small>{hint}</small>
    </label>
  );
}

function OptionField({
  label,
  name,
  options,
  loading,
  required = false,
  defaultValue,
  emptyLabel,
}: {
  label: string;
  name: string;
  options: Array<{ id: number; label: string }>;
  loading: boolean;
  required?: boolean;
  defaultValue?: number;
  emptyLabel?: string;
}) {
  return (
    <label className="field">
      <span>
        {label} {required && <b>*</b>}
      </span>
      <select
        key={`${name}:${loading ? "loading" : (defaultValue ?? "empty")}`}
        name={name}
        required={required}
        defaultValue={defaultValue ?? ""}
        disabled={loading}
      >
        <option value="">
          {loading ? "Loading choices" : (emptyLabel ?? "Select a value")}
        </option>
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
      <small />
    </label>
  );
}
