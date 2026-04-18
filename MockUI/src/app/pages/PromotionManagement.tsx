import { useState } from "react";
import { TrendingUp, Clock, Settings, CheckCircle, XCircle, Calendar } from "lucide-react";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Label } from "../components/ui/label";
import { Input } from "../components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";

const promotionRules = [
  { level: "L7 → L6", baseMonths: 36, baseSalaryIncrease: "15%" },
  { level: "L6 → L5", baseMonths: 48, baseSalaryIncrease: "20%" },
  { level: "L5 → L4", baseMonths: 60, baseSalaryIncrease: "25%" },
];

const eligibleEmployees = [
  {
    id: "EMP-1001",
    name: "Emily Davis",
    currentLevel: "L7",
    nextLevel: "L6",
    yearsInLevel: 3.2,
    commendations: 3,
    eligibleDate: "2024-04-15",
    status: "Eligible",
    progress: 100,
  },
  {
    id: "EMP-1002",
    name: "Robert Wilson",
    currentLevel: "L6",
    nextLevel: "L5",
    yearsInLevel: 4.5,
    commendations: 4,
    eligibleDate: "2024-03-20",
    status: "Eligible",
    progress: 100,
  },
  {
    id: "EMP-1003",
    name: "Lisa Anderson",
    currentLevel: "L7",
    nextLevel: "L6",
    yearsInLevel: 2.8,
    commendations: 2,
    eligibleDate: "2024-06-10",
    status: "Soon",
    progress: 85,
  },
  {
    id: "EMP-1004",
    name: "Michael Brown",
    currentLevel: "L7",
    nextLevel: "L6",
    yearsInLevel: 1.5,
    commendations: 1,
    eligibleDate: "2025-09-15",
    status: "In Progress",
    progress: 45,
  },
];

const promotionHistory = [
  {
    id: 1,
    employeeId: "EMP-1001",
    employeeName: "John Smith",
    fromLevel: "L7",
    toLevel: "L6",
    date: "2024-01-15",
    approvedBy: "Admin User",
    reason: "Met requirements: 3 years service + 2 commendations",
  },
  {
    id: 2,
    employeeId: "EMP-1005",
    employeeName: "Sarah Johnson",
    fromLevel: "L6",
    toLevel: "L5",
    date: "2023-11-20",
    approvedBy: "HR Officer",
    reason: "Met requirements: 4 years service + 3 commendations",
  },
  {
    id: 3,
    employeeId: "EMP-1008",
    employeeName: "David Martinez",
    fromLevel: "L5",
    toLevel: "L4",
    date: "2023-09-10",
    approvedBy: "Admin User",
    reason: "Met requirements: 5 years service + 4 commendations",
  },
];

export function PromotionManagement() {
  const [isEditingRules, setIsEditingRules] = useState(false);

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Promotion Management</h1>
        <p className="text-gray-600">Manage promotion rules and track employee eligibility</p>
      </div>

      <Tabs defaultValue="eligible" className="space-y-6">
        <TabsList>
          <TabsTrigger value="eligible">Eligible Employees</TabsTrigger>
          <TabsTrigger value="history">Promotion History</TabsTrigger>
          <TabsTrigger value="rules">Promotion Rules</TabsTrigger>
        </TabsList>

        {/* Eligible Employees */}
        <TabsContent value="eligible">
          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <Card className="p-6">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                  <CheckCircle className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Eligible Now</p>
                  <p className="text-2xl font-bold text-gray-900">2</p>
                </div>
              </div>
            </Card>
            <Card className="p-6">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                  <Clock className="w-6 h-6 text-yellow-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">Eligible Soon</p>
                  <p className="text-2xl font-bold text-gray-900">1</p>
                </div>
              </div>
            </Card>
            <Card className="p-6">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-600">In Progress</p>
                  <p className="text-2xl font-bold text-gray-900">1</p>
                </div>
              </div>
            </Card>
          </div>

          {/* Table */}
          <Card>
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Employee Promotion Tracker</h3>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Employee</TableHead>
                  <TableHead>Current Level</TableHead>
                  <TableHead>Next Level</TableHead>
                  <TableHead>Years in Level</TableHead>
                  <TableHead>Commendations</TableHead>
                  <TableHead>Eligible Date</TableHead>
                  <TableHead>Progress</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {eligibleEmployees.map((emp) => (
                  <TableRow key={emp.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium text-gray-900">{emp.name}</p>
                        <p className="text-sm text-gray-500">{emp.id}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">
                        {emp.currentLevel}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                        {emp.nextLevel}
                      </Badge>
                    </TableCell>
                    <TableCell>{emp.yearsInLevel} years</TableCell>
                    <TableCell>{emp.commendations}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-gray-400" />
                        <span className="text-sm">{emp.eligibleDate}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div>
                        <div className="w-full bg-gray-200 rounded-full h-2 mb-1">
                          <div
                            className={`h-2 rounded-full transition-all ${
                              emp.progress === 100
                                ? "bg-green-600"
                                : emp.progress > 70
                                ? "bg-yellow-600"
                                : "bg-blue-600"
                            }`}
                            style={{ width: `${emp.progress}%` }}
                          ></div>
                        </div>
                        <p className="text-xs text-gray-500">{emp.progress}%</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-2">
                        {emp.status === "Eligible" ? (
                          <>
                            <Button size="sm" className="gap-2">
                              <CheckCircle className="w-4 h-4" />
                              Approve
                            </Button>
                            <Button variant="outline" size="sm" className="gap-2">
                              <XCircle className="w-4 h-4" />
                              Defer
                            </Button>
                          </>
                        ) : (
                          <Button variant="ghost" size="sm">
                            View Details
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* Promotion History */}
        <TabsContent value="history">
          <Card>
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Recent Promotions</h3>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Employee</TableHead>
                  <TableHead>Promotion</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Approved By</TableHead>
                  <TableHead>Reason</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {promotionHistory.map((promo) => (
                  <TableRow key={promo.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium text-gray-900">{promo.employeeName}</p>
                        <p className="text-sm text-gray-500">{promo.employeeId}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Badge className="bg-gray-100 text-gray-700 hover:bg-gray-100">
                          {promo.fromLevel}
                        </Badge>
                        <TrendingUp className="w-4 h-4 text-green-600" />
                        <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                          {promo.toLevel}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell>{promo.date}</TableCell>
                    <TableCell>{promo.approvedBy}</TableCell>
                    <TableCell className="text-sm text-gray-600">{promo.reason}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* Promotion Rules */}
        <TabsContent value="rules">
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Promotion Track Configuration</h3>
                <p className="text-sm text-gray-600 mt-1">Configure the promotion race timeline for each level</p>
              </div>
              <Button
                variant={isEditingRules ? "default" : "outline"}
                className="gap-2"
                onClick={() => setIsEditingRules(!isEditingRules)}
              >
                <Settings className="w-4 h-4" />
                {isEditingRules ? "Save Changes" : "Edit Rules"}
              </Button>
            </div>

            {/* Race Metaphor Explanation */}
            <div className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg">
              <div className="flex items-start gap-3">
                <TrendingUp className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-blue-900">
                  <p className="font-semibold mb-2">How the Promotion Race Works</p>
                  <div className="space-y-1">
                    <p>• Each promotion level is a <strong>race track</strong> with a base duration in months</p>
                    <p>• Employees move forward <strong>1 checkpoint per month</strong> automatically</p>
                    <p>• <strong>Commendations</strong> speed up the race (reduce months remaining)</p>
                    <p>• <strong>Sanctions</strong> delay the race (add months to the timeline)</p>
                    <p>• When the employee reaches the finish line (0 months remaining), they become eligible for promotion</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-6">
              {promotionRules.map((rule, index) => (
                <div key={index} className="p-6 bg-gray-50 rounded-lg border border-gray-200">
                  <h4 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-blue-600" />
                    {rule.level}
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor={`months-${index}`}>
                        Base Track Duration (months)
                      </Label>
                      <Input
                        id={`months-${index}`}
                        type="number"
                        value={rule.baseMonths}
                        disabled={!isEditingRules}
                        className="mt-1"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Starting point for the promotion race
                      </p>
                    </div>
                    <div>
                      <Label htmlFor={`salary-${index}`}>Base Salary Increase</Label>
                      <Input
                        id={`salary-${index}`}
                        value={rule.baseSalaryIncrease}
                        disabled={!isEditingRules}
                        className="mt-1"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Upon promotion to next level
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-start gap-3">
                <Clock className="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-yellow-800">
                  <p className="font-semibold mb-1">Track Modifiers (Optional)</p>
                  <p>
                    • Commendations are <strong>optional accelerators</strong> that reduce the months remaining in the race
                  </p>
                  <p>
                    • Sanctions are <strong>optional delays</strong> that add months to the race timeline
                  </p>
                  <p className="mt-2 text-xs italic">
                    Configure commendation categories and sanction impacts in their respective pages
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
              <div className="flex items-start gap-3">
                <TrendingUp className="w-5 h-5 text-purple-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-purple-800">
                  <p className="font-semibold mb-1">Reset Policy</p>
                  <p>After a promotion, the employee starts a new race from month 0. The timer for the next promotion begins from the promotion date.</p>
                </div>
              </div>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
