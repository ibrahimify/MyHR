import { Users, TrendingUp, Award, AlertTriangle, UserPlus, Calendar } from "lucide-react";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Link } from "react-router";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from "recharts";

const stats = [
  {
    name: "Total Employees",
    value: "1,247",
    change: "+12%",
    changeType: "positive",
    icon: Users,
    color: "bg-blue-500",
  },
  {
    name: "Pending Promotions",
    value: "23",
    change: "+5",
    changeType: "neutral",
    icon: TrendingUp,
    color: "bg-green-500",
  },
  {
    name: "Commendations (This Month)",
    value: "47",
    change: "+18%",
    changeType: "positive",
    icon: Award,
    color: "bg-yellow-500",
  },
  {
    name: "Active Sanctions",
    value: "8",
    change: "-2",
    changeType: "positive",
    icon: AlertTriangle,
    color: "bg-red-500",
  },
];

const departmentData = [
  { id: "dept-1", name: "IT", employees: 245 },
  { id: "dept-2", name: "HR", employees: 89 },
  { id: "dept-3", name: "Finance", employees: 156 },
  { id: "dept-4", name: "Operations", employees: 312 },
  { id: "dept-5", name: "Marketing", employees: 178 },
  { id: "dept-6", name: "Sales", employees: 267 },
];

const promotionTrend = [
  { id: "month-1", month: "Jan", promotions: 12 },
  { id: "month-2", month: "Feb", promotions: 19 },
  { id: "month-3", month: "Mar", promotions: 15 },
  { id: "month-4", month: "Apr", promotions: 23 },
  { id: "month-5", month: "May", promotions: 18 },
  { id: "month-6", month: "Jun", promotions: 25 },
];

const recentActivities = [
  {
    id: 1,
    action: "Employee Added",
    user: "Admin User",
    target: "John Smith (EMP-1248)",
    time: "2 hours ago",
  },
  {
    id: 2,
    action: "Promotion Approved",
    user: "HR Officer",
    target: "Sarah Johnson → L6",
    time: "4 hours ago",
  },
  {
    id: 3,
    action: "Commendation Issued",
    user: "Admin User",
    target: "5 employees (Team Award)",
    time: "6 hours ago",
  },
  {
    id: 4,
    action: "Sanction Applied",
    user: "HR Officer",
    target: "Michael Brown (Warning)",
    time: "1 day ago",
  },
  {
    id: 5,
    action: "CSV Import",
    user: "Admin User",
    target: "45 employees imported",
    time: "2 days ago",
  },
];

const upcomingPromotions = [
  { id: 1, name: "Emily Davis", currentLevel: "L7", nextLevel: "L6", eligibleIn: "14 days", progress: 85 },
  { id: 2, name: "Robert Wilson", currentLevel: "L6", nextLevel: "L5", eligibleIn: "28 days", progress: 70 },
  { id: 3, name: "Lisa Anderson", currentLevel: "L7", nextLevel: "L6", eligibleIn: "45 days", progress: 55 },
];

export function Dashboard() {
  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
        <p className="text-gray-600">Welcome back! Here's what's happening with your organization.</p>
      </div>

      {/* Quick Actions */}
      <div className="mb-8 flex gap-3">
        <Link to="/employees/new">
          <Button className="gap-2">
            <UserPlus className="w-4 h-4" />
            Add Employee
          </Button>
        </Link>
        <Link to="/import">
          <Button variant="outline" className="gap-2">
            <Calendar className="w-4 h-4" />
            Import Data
          </Button>
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat) => (
          <Card key={stat.name} className="p-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">{stat.name}</p>
                <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
                <p className={`text-sm mt-2 ${
                  stat.changeType === "positive" ? "text-green-600" : 
                  stat.changeType === "negative" ? "text-red-600" : "text-gray-600"
                }`}>
                  {stat.change} from last month
                </p>
              </div>
              <div className={`${stat.color} p-3 rounded-lg`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Department Distribution */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Employees by Department</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={departmentData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="employees" fill="#3b82f6" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Promotion Trend */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Promotion Trend (6 Months)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={promotionTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Line type="monotone" dataKey="promotions" stroke="#10b981" strokeWidth={3} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Bottom Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activities */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Recent Activities</h3>
            <Link to="/audit">
              <Button variant="ghost" size="sm">View All</Button>
            </Link>
          </div>
          <div className="space-y-4">
            {recentActivities.map((activity) => (
              <div key={activity.id} className="flex gap-4 pb-4 border-b border-gray-100 last:border-0 last:pb-0">
                <div className="w-2 h-2 bg-blue-600 rounded-full mt-2"></div>
                <div className="flex-1">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{activity.action}</p>
                      <p className="text-sm text-gray-600">{activity.target}</p>
                      <p className="text-xs text-gray-500 mt-1">by {activity.user}</p>
                    </div>
                    <span className="text-xs text-gray-500">{activity.time}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Upcoming Promotions */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Upcoming Eligible Promotions</h3>
            <Link to="/promotions">
              <Button variant="ghost" size="sm">View All</Button>
            </Link>
          </div>
          <div className="space-y-4">
            {upcomingPromotions.map((promo) => (
              <div key={promo.id} className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-medium text-gray-900">{promo.name}</p>
                    <p className="text-sm text-gray-600">
                      {promo.currentLevel} → {promo.nextLevel}
                    </p>
                  </div>
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">
                    {promo.eligibleIn}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all" 
                    style={{ width: `${promo.progress}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-500 mt-1">{promo.progress}% complete</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}