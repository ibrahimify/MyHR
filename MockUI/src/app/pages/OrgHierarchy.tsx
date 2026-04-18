import { useState } from "react";
import { Building2, ChevronRight, ChevronDown, Users, Plus, Edit, Trash2 } from "lucide-react";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";

interface OrgNode {
  id: string;
  name: string;
  type: "organization" | "division" | "department" | "unit" | "team" | "position";
  head?: string;
  employeeCount: number;
  children?: OrgNode[];
}

const orgData: OrgNode = {
  id: "org-1",
  name: "MyHR Company",
  type: "organization",
  head: "CEO - David Martinez",
  employeeCount: 1247,
  children: [
    {
      id: "div-1",
      name: "Technology Division",
      type: "division",
      head: "CTO - John Smith",
      employeeCount: 450,
      children: [
        {
          id: "dept-1",
          name: "Information Technology Department",
          type: "department",
          head: "IT Director - Sarah Johnson",
          employeeCount: 245,
          children: [
            {
              id: "unit-1",
              name: "Software Development Unit",
              type: "unit",
              head: "Dev Manager - Michael Brown",
              employeeCount: 120,
              children: [
                {
                  id: "team-1",
                  name: "Frontend Team",
                  type: "team",
                  head: "Team Lead - Emily Davis",
                  employeeCount: 45,
                  children: [
                    {
                      id: "pos-1",
                      name: "Senior Frontend Developer",
                      type: "position",
                      employeeCount: 8,
                    },
                    {
                      id: "pos-2",
                      name: "Mid-Level Frontend Developer",
                      type: "position",
                      employeeCount: 15,
                    },
                    {
                      id: "pos-3",
                      name: "Junior Frontend Developer",
                      type: "position",
                      employeeCount: 12,
                    },
                    {
                      id: "pos-4",
                      name: "Frontend Intern",
                      type: "position",
                      employeeCount: 10,
                    },
                  ],
                },
                {
                  id: "team-2",
                  name: "Backend Team",
                  type: "team",
                  head: "Team Lead - Robert Wilson",
                  employeeCount: 50,
                  children: [
                    {
                      id: "pos-5",
                      name: "Senior Backend Developer",
                      type: "position",
                      employeeCount: 10,
                    },
                    {
                      id: "pos-6",
                      name: "Mid-Level Backend Developer",
                      type: "position",
                      employeeCount: 18,
                    },
                    {
                      id: "pos-7",
                      name: "Junior Backend Developer",
                      type: "position",
                      employeeCount: 12,
                    },
                    {
                      id: "pos-8",
                      name: "Backend Intern",
                      type: "position",
                      employeeCount: 10,
                    },
                  ],
                },
                {
                  id: "team-3",
                  name: "QA Team",
                  type: "team",
                  head: "QA Lead - Lisa Anderson",
                  employeeCount: 25,
                },
              ],
            },
            {
              id: "unit-2",
              name: "Infrastructure & Security Unit",
              type: "unit",
              head: "Security Head - James Martinez",
              employeeCount: 85,
              children: [
                {
                  id: "team-4",
                  name: "Network Team",
                  type: "team",
                  head: "Network Manager - Patricia Lee",
                  employeeCount: 30,
                },
                {
                  id: "team-5",
                  name: "Security Team",
                  type: "team",
                  head: "Security Manager - Thomas Garcia",
                  employeeCount: 35,
                },
                {
                  id: "team-6",
                  name: "DevOps Team",
                  type: "team",
                  head: "DevOps Lead - Amanda White",
                  employeeCount: 20,
                },
              ],
            },
            {
              id: "unit-3",
              name: "IT Support Unit",
              type: "unit",
              head: "Support Manager - Christopher Brown",
              employeeCount: 40,
            },
          ],
        },
        {
          id: "dept-2",
          name: "Research & Development Department",
          type: "department",
          head: "R&D Director - Jennifer Wilson",
          employeeCount: 205,
          children: [
            {
              id: "unit-8",
              name: "AI Research Unit",
              type: "unit",
              head: "AI Lead - Maria Anderson",
              employeeCount: 85,
            },
            {
              id: "unit-9",
              name: "Product Innovation Unit",
              type: "unit",
              head: "Innovation Manager - Daniel Taylor",
              employeeCount: 120,
            },
          ],
        },
      ],
    },
    {
      id: "div-2",
      name: "Business Operations Division",
      type: "division",
      head: "COO - Elizabeth Johnson",
      employeeCount: 797,
      children: [
        {
          id: "dept-3",
          name: "Human Resources Department",
          type: "department",
          head: "HR Director - William Smith",
          employeeCount: 89,
          children: [
            {
              id: "unit-4",
              name: "Recruitment Unit",
              type: "unit",
              head: "Recruitment Manager - Sophia Davis",
              employeeCount: 35,
            },
            {
              id: "unit-5",
              name: "Employee Relations Unit",
              type: "unit",
              head: "Relations Manager - Oliver Martinez",
              employeeCount: 54,
            },
          ],
        },
        {
          id: "dept-4",
          name: "Finance Department",
          type: "department",
          head: "CFO - Isabella Wilson",
          employeeCount: 156,
          children: [
            {
              id: "unit-6",
              name: "Accounting Unit",
              type: "unit",
              head: "Chief Accountant - Ethan Brown",
              employeeCount: 78,
            },
            {
              id: "unit-7",
              name: "Financial Planning Unit",
              type: "unit",
              head: "Planning Director - Ava Garcia",
              employeeCount: 78,
            },
          ],
        },
        {
          id: "dept-5",
          name: "Operations Department",
          type: "department",
          head: "Operations Director - Noah Anderson",
          employeeCount: 312,
        },
        {
          id: "dept-6",
          name: "Marketing Department",
          type: "department",
          head: "CMO - Emma Taylor",
          employeeCount: 178,
        },
        {
          id: "dept-7",
          name: "Sales Department",
          type: "department",
          head: "Sales Director - Liam Lee",
          employeeCount: 267,
        },
      ],
    },
  ],
};

function TreeNode({ node, level = 0 }: { node: OrgNode; level?: number }) {
  const [isExpanded, setIsExpanded] = useState(level < 2);

  const getTypeColor = (type: string) => {
    switch (type) {
      case "organization":
        return "bg-purple-100 text-purple-700 border-purple-200";
      case "division":
        return "bg-orange-100 text-orange-700 border-orange-200";
      case "department":
        return "bg-blue-100 text-blue-700 border-blue-200";
      case "unit":
        return "bg-green-100 text-green-700 border-green-200";
      case "team":
        return "bg-gray-100 text-gray-700 border-gray-200";
      case "position":
        return "bg-gray-100 text-gray-700 border-gray-200";
      default:
        return "bg-gray-100 text-gray-700 border-gray-200";
    }
  };

  const hasChildren = node.children && node.children.length > 0;

  return (
    <div className="ml-6">
      <div className="flex items-center gap-3 py-3 group">
        {/* Expand/Collapse Button */}
        {hasChildren ? (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-6 h-6 flex items-center justify-center hover:bg-gray-100 rounded transition-colors"
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-600" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-600" />
            )}
          </button>
        ) : (
          <div className="w-6" />
        )}

        {/* Node Content */}
        <div className={`flex-1 p-4 rounded-lg border-2 ${getTypeColor(node.type)} transition-all`}>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <Building2 className="w-5 h-5" />
                <h4 className="font-semibold text-gray-900">{node.name}</h4>
                <Badge variant="outline" className="text-xs">
                  {node.type}
                </Badge>
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-600">
                {node.head && (
                  <div className="flex items-center gap-1">
                    <span className="font-medium">Head:</span>
                    <span>{node.head}</span>
                  </div>
                )}
                <div className="flex items-center gap-1">
                  <Users className="w-4 h-4" />
                  <span>{node.employeeCount} employees</span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button variant="ghost" size="sm">
                <Plus className="w-4 h-4" />
              </Button>
              <Button variant="ghost" size="sm">
                <Edit className="w-4 h-4" />
              </Button>
              <Button variant="ghost" size="sm" className="text-red-600 hover:text-red-700">
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Children */}
      {hasChildren && isExpanded && (
        <div className="border-l-2 border-gray-200 ml-3">
          {node.children!.map((child) => (
            <TreeNode key={child.id} node={child} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export function OrgHierarchy() {
  const [searchQuery, setSearchQuery] = useState("");

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Organization Hierarchy</h1>
        <p className="text-gray-600">View and manage the organizational structure</p>
      </div>

      {/* Controls */}
      <Card className="p-4 mb-6">
        <div className="flex items-center justify-between gap-4">
          <Input
            placeholder="Search departments, units, or positions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="max-w-md"
          />
          <div className="flex gap-3">
            <Button variant="outline" className="gap-2">
              <Building2 className="w-4 h-4" />
              Add Department
            </Button>
            <Button className="gap-2">
              <Plus className="w-4 h-4" />
              Add Unit
            </Button>
          </div>
        </div>
      </Card>

      {/* Legend */}
      <div className="mb-6 flex items-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-purple-100 border-2 border-purple-200"></div>
          <span className="text-gray-600">Organization</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-orange-100 border-2 border-orange-200"></div>
          <span className="text-gray-600">Division</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-blue-100 border-2 border-blue-200"></div>
          <span className="text-gray-600">Department</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-green-100 border-2 border-green-200"></div>
          <span className="text-gray-600">Unit</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-gray-100 border-2 border-gray-200"></div>
          <span className="text-gray-600">Team</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-gray-100 border-2 border-gray-200"></div>
          <span className="text-gray-600">Position</span>
        </div>
      </div>

      {/* Tree */}
      <Card className="p-6">
        <TreeNode node={orgData} level={0} />
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
        <Card className="p-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <Building2 className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Departments</p>
              <p className="text-2xl font-bold text-gray-900">6</p>
            </div>
          </div>
        </Card>
        <Card className="p-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <Building2 className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Units</p>
              <p className="text-2xl font-bold text-gray-900">7</p>
            </div>
          </div>
        </Card>
        <Card className="p-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
              <Users className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Employees</p>
              <p className="text-2xl font-bold text-gray-900">1,247</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}