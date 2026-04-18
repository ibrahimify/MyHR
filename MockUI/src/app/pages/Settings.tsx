import { useState } from "react";
import { Settings as SettingsIcon, Save, Building2, DollarSign, TrendingUp, Bell, Shield, Database, Calendar } from "lucide-react";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Switch } from "../components/ui/switch";
import { Separator } from "../components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";

export function Settings() {
  const [generalSettings, setGeneralSettings] = useState({
    companyName: "MyHR Company",
    companyAddress: "Budapest, Hungary",
    fiscalYearStart: "01-01",
    timezone: "Europe/Budapest",
  });

  const [salarySettings, setSalarySettings] = useState({
    l7Min: "2000",
    l7Max: "2800",
    l6Min: "2800",
    l6Max: "3500",
    l5Min: "3500",
    l5Max: "4500",
    l4Min: "4500",
    l4Max: "6000",
    currency: "EUR",
    annualIncrementType: "percentage",
    annualIncrementValue: "3",
  });

  const [promotionSettings, setPromotionSettings] = useState({
    l7ToL6Years: "3",
    l7ToL6Commendations: "2",
    l6ToL5Years: "4",
    l6ToL5Commendations: "3",
    l5ToL4Years: "5",
    l5ToL4Commendations: "4",
    autoResetCommendations: true,
  });

  const [notifications, setNotifications] = useState({
    emailNotifications: true,
    promotionAlerts: true,
    sanctionAlerts: true,
    commendationAlerts: false,
    weeklyReports: true,
  });

  const [securitySettings, setSecuritySettings] = useState({
    sessionTimeout: "30",
    passwordExpiry: "90",
    twoFactorAuth: false,
    auditLogRetention: "indefinite",
  });

  const handleSaveGeneral = () => {
    alert("General settings saved successfully");
  };

  const handleSaveSalary = () => {
    alert("Salary settings saved successfully");
  };

  const handleSavePromotion = () => {
    alert("Promotion settings saved successfully");
  };

  const handleSaveNotifications = () => {
    alert("Notification settings saved successfully");
  };

  const handleSaveSecurity = () => {
    alert("Security settings saved successfully");
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">System Settings</h1>
        <p className="text-gray-600">Configure system preferences and business rules</p>
      </div>

      <Tabs defaultValue="general" className="space-y-6">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="salary">Salary Ranges</TabsTrigger>
          <TabsTrigger value="promotion">Promotion Rules</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
        </TabsList>

        {/* General Settings */}
        <TabsContent value="general">
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <Building2 className="w-6 h-6 text-blue-600" />
              <h3 className="text-lg font-semibold text-gray-900">Organization Information</h3>
            </div>

            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="companyName">Company Name</Label>
                  <Input
                    id="companyName"
                    value={generalSettings.companyName}
                    onChange={(e) => setGeneralSettings({ ...generalSettings, companyName: e.target.value })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="companyAddress">Company Address</Label>
                  <Input
                    id="companyAddress"
                    value={generalSettings.companyAddress}
                    onChange={(e) => setGeneralSettings({ ...generalSettings, companyAddress: e.target.value })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="fiscalYearStart">Fiscal Year Start (MM-DD)</Label>
                  <Input
                    id="fiscalYearStart"
                    placeholder="01-01"
                    value={generalSettings.fiscalYearStart}
                    onChange={(e) => setGeneralSettings({ ...generalSettings, fiscalYearStart: e.target.value })}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="timezone">Timezone</Label>
                  <Input
                    id="timezone"
                    value={generalSettings.timezone}
                    onChange={(e) => setGeneralSettings({ ...generalSettings, timezone: e.target.value })}
                    className="mt-1"
                  />
                </div>
              </div>

              <Separator />

              <div className="flex justify-end">
                <Button onClick={handleSaveGeneral} className="gap-2">
                  <Save className="w-4 h-4" />
                  Save General Settings
                </Button>
              </div>
            </div>
          </Card>
        </TabsContent>

        {/* Salary Ranges */}
        <TabsContent value="salary">
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <DollarSign className="w-6 h-6 text-green-600" />
              <h3 className="text-lg font-semibold text-gray-900">Salary Range Configuration</h3>
            </div>

            <div className="space-y-6">
              <div>
                <Label htmlFor="currency">Currency</Label>
                <Input
                  id="currency"
                  value={salarySettings.currency}
                  onChange={(e) => setSalarySettings({ ...salarySettings, currency: e.target.value })}
                  className="mt-1 max-w-xs"
                />
              </div>

              <Separator />

              {/* Annual Salary Increment */}
              <div className="p-4 bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg">
                <div className="flex items-start gap-3 mb-4">
                  <Calendar className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <h4 className="font-semibold text-green-900 mb-1">Annual Salary Increment</h4>
                    <p className="text-sm text-green-700 mb-3">
                      Automatic yearly salary increase (separate from promotions)
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="annualIncrementType">Increment Type</Label>
                        <Select
                          value={salarySettings.annualIncrementType}
                          onValueChange={(val) => setSalarySettings({ ...salarySettings, annualIncrementType: val })}
                        >
                          <SelectTrigger className="mt-1 bg-white">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="percentage">Percentage (%)</SelectItem>
                            <SelectItem value="fixed">Fixed Amount</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label htmlFor="annualIncrementValue">
                          {salarySettings.annualIncrementType === "percentage" ? "Percentage" : "Amount"}
                        </Label>
                        <div className="flex gap-2 mt-1">
                          <Input
                            id="annualIncrementValue"
                            type="number"
                            step="0.1"
                            value={salarySettings.annualIncrementValue}
                            onChange={(e) => setSalarySettings({ ...salarySettings, annualIncrementValue: e.target.value })}
                            className="bg-white"
                          />
                          <span className="px-3 py-2 bg-white rounded border border-gray-300 text-gray-700">
                            {salarySettings.annualIncrementType === "percentage" ? "%" : salarySettings.currency}
                          </span>
                        </div>
                      </div>
                    </div>

                    <p className="text-xs text-green-700 mt-3 italic">
                      Example: With 3% annual increment, a salary of €2,000 becomes €2,060 after 1 year (regardless of promotion status)
                    </p>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Level Salary Ranges */}
              <div className="space-y-4">
                {/* L7 */}
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <h4 className="font-semibold text-blue-900 mb-3 flex items-center gap-2">
                    <span className="px-2 py-1 bg-blue-600 text-white rounded text-sm">L7</span>
                    Entry Level (BSc)
                  </h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="l7Min">Minimum Salary</Label>
                      <div className="flex gap-2 mt-1">
                        <Input
                          id="l7Min"
                          type="number"
                          value={salarySettings.l7Min}
                          onChange={(e) => setSalarySettings({ ...salarySettings, l7Min: e.target.value })}
                        />
                        <span className="px-3 py-2 bg-gray-100 rounded border border-gray-300 text-gray-700">
                          {salarySettings.currency}
                        </span>
                      </div>
                    </div>
                    <div>
                      <Label htmlFor="l7Max">Maximum Salary</Label>
                      <div className="flex gap-2 mt-1">
                        <Input
                          id="l7Max"
                          type="number"
                          value={salarySettings.l7Max}
                          onChange={(e) => setSalarySettings({ ...salarySettings, l7Max: e.target.value })}
                        />
                        <span className="px-3 py-2 bg-gray-100 rounded border border-gray-300 text-gray-700">
                          {salarySettings.currency}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* L6 */}
                <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                  <h4 className="font-semibold text-green-900 mb-3 flex items-center gap-2">
                    <span className="px-2 py-1 bg-green-600 text-white rounded text-sm">L6</span>
                    Mid Level (MSc)
                  </h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="l6Min">Minimum Salary</Label>
                      <div className="flex gap-2 mt-1">
                        <Input
                          id="l6Min"
                          type="number"
                          value={salarySettings.l6Min}
                          onChange={(e) => setSalarySettings({ ...salarySettings, l6Min: e.target.value })}
                        />
                        <span className="px-3 py-2 bg-gray-100 rounded border border-gray-300 text-gray-700">
                          {salarySettings.currency}
                        </span>
                      </div>
                    </div>
                    <div>
                      <Label htmlFor="l6Max">Maximum Salary</Label>
                      <div className="flex gap-2 mt-1">
                        <Input
                          id="l6Max"
                          type="number"
                          value={salarySettings.l6Max}
                          onChange={(e) => setSalarySettings({ ...salarySettings, l6Max: e.target.value })}
                        />
                        <span className="px-3 py-2 bg-gray-100 rounded border border-gray-300 text-gray-700">
                          {salarySettings.currency}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* L5 */}
                <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                  <h4 className="font-semibold text-yellow-900 mb-3 flex items-center gap-2">
                    <span className="px-2 py-1 bg-yellow-600 text-white rounded text-sm">L5</span>
                    Senior Level (PhD)
                  </h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="l5Min">Minimum Salary</Label>
                      <div className="flex gap-2 mt-1">
                        <Input
                          id="l5Min"
                          type="number"
                          value={salarySettings.l5Min}
                          onChange={(e) => setSalarySettings({ ...salarySettings, l5Min: e.target.value })}
                        />
                        <span className="px-3 py-2 bg-gray-100 rounded border border-gray-300 text-gray-700">
                          {salarySettings.currency}
                        </span>
                      </div>
                    </div>
                    <div>
                      <Label htmlFor="l5Max">Maximum Salary</Label>
                      <div className="flex gap-2 mt-1">
                        <Input
                          id="l5Max"
                          type="number"
                          value={salarySettings.l5Max}
                          onChange={(e) => setSalarySettings({ ...salarySettings, l5Max: e.target.value })}
                        />
                        <span className="px-3 py-2 bg-gray-100 rounded border border-gray-300 text-gray-700">
                          {salarySettings.currency}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* L4 */}
                <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                  <h4 className="font-semibold text-purple-900 mb-3 flex items-center gap-2">
                    <span className="px-2 py-1 bg-purple-600 text-white rounded text-sm">L4</span>
                    Management Level
                  </h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="l4Min">Minimum Salary</Label>
                      <div className="flex gap-2 mt-1">
                        <Input
                          id="l4Min"
                          type="number"
                          value={salarySettings.l4Min}
                          onChange={(e) => setSalarySettings({ ...salarySettings, l4Min: e.target.value })}
                        />
                        <span className="px-3 py-2 bg-gray-100 rounded border border-gray-300 text-gray-700">
                          {salarySettings.currency}
                        </span>
                      </div>
                    </div>
                    <div>
                      <Label htmlFor="l4Max">Maximum Salary</Label>
                      <div className="flex gap-2 mt-1">
                        <Input
                          id="l4Max"
                          type="number"
                          value={salarySettings.l4Max}
                          onChange={(e) => setSalarySettings({ ...salarySettings, l4Max: e.target.value })}
                        />
                        <span className="px-3 py-2 bg-gray-100 rounded border border-gray-300 text-gray-700">
                          {salarySettings.currency}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <Separator />

              <div className="flex justify-end">
                <Button onClick={handleSaveSalary} className="gap-2">
                  <Save className="w-4 h-4" />
                  Save Salary Settings
                </Button>
              </div>
            </div>
          </Card>
        </TabsContent>

        {/* Promotion Rules */}
        <TabsContent value="promotion">
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <TrendingUp className="w-6 h-6 text-green-600" />
              <h3 className="text-lg font-semibold text-gray-900">Promotion Eligibility Rules</h3>
            </div>

            <div className="space-y-6">
              {/* L7 → L6 */}
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <h4 className="font-semibold text-blue-900 mb-3">L7 → L6 Promotion</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="l7ToL6Years">Years Required in Level</Label>
                    <Input
                      id="l7ToL6Years"
                      type="number"
                      value={promotionSettings.l7ToL6Years}
                      onChange={(e) => setPromotionSettings({ ...promotionSettings, l7ToL6Years: e.target.value })}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="l7ToL6Commendations">Commendations Required</Label>
                    <Input
                      id="l7ToL6Commendations"
                      type="number"
                      value={promotionSettings.l7ToL6Commendations}
                      onChange={(e) => setPromotionSettings({ ...promotionSettings, l7ToL6Commendations: e.target.value })}
                      className="mt-1"
                    />
                  </div>
                </div>
              </div>

              {/* L6 → L5 */}
              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <h4 className="font-semibold text-green-900 mb-3">L6 → L5 Promotion</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="l6ToL5Years">Years Required in Level</Label>
                    <Input
                      id="l6ToL5Years"
                      type="number"
                      value={promotionSettings.l6ToL5Years}
                      onChange={(e) => setPromotionSettings({ ...promotionSettings, l6ToL5Years: e.target.value })}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="l6ToL5Commendations">Commendations Required</Label>
                    <Input
                      id="l6ToL5Commendations"
                      type="number"
                      value={promotionSettings.l6ToL5Commendations}
                      onChange={(e) => setPromotionSettings({ ...promotionSettings, l6ToL5Commendations: e.target.value })}
                      className="mt-1"
                    />
                  </div>
                </div>
              </div>

              {/* L5 → L4 */}
              <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                <h4 className="font-semibold text-yellow-900 mb-3">L5 → L4 Promotion</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="l5ToL4Years">Years Required in Level</Label>
                    <Input
                      id="l5ToL4Years"
                      type="number"
                      value={promotionSettings.l5ToL4Years}
                      onChange={(e) => setPromotionSettings({ ...promotionSettings, l5ToL4Years: e.target.value })}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="l5ToL4Commendations">Commendations Required</Label>
                    <Input
                      id="l5ToL4Commendations"
                      type="number"
                      value={promotionSettings.l5ToL4Commendations}
                      onChange={(e) => setPromotionSettings({ ...promotionSettings, l5ToL4Commendations: e.target.value })}
                      className="mt-1"
                    />
                  </div>
                </div>
              </div>

              <Separator />

              {/* Reset Policy */}
              <div className="flex items-center justify-between p-4 bg-purple-50 rounded-lg border border-purple-200">
                <div>
                  <h4 className="font-semibold text-purple-900 mb-1">Auto-Reset Commendations After Promotion</h4>
                  <p className="text-sm text-purple-700">
                    When enabled, commendation count resets to zero after each promotion
                  </p>
                </div>
                <Switch
                  checked={promotionSettings.autoResetCommendations}
                  onCheckedChange={(checked) =>
                    setPromotionSettings({ ...promotionSettings, autoResetCommendations: checked })
                  }
                />
              </div>

              <Separator />

              <div className="flex justify-end">
                <Button onClick={handleSavePromotion} className="gap-2">
                  <Save className="w-4 h-4" />
                  Save Promotion Settings
                </Button>
              </div>
            </div>
          </Card>
        </TabsContent>

        {/* Notifications */}
        <TabsContent value="notifications">
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <Bell className="w-6 h-6 text-yellow-600" />
              <h3 className="text-lg font-semibold text-gray-900">Notification Preferences</h3>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 rounded-lg border border-gray-200">
                <div>
                  <h4 className="font-medium text-gray-900">Promotion Eligibility Alerts</h4>
                  <p className="text-sm text-gray-600">Desktop alerts when employees become eligible for promotion</p>
                </div>
                <Switch
                  checked={notifications.promotionAlerts}
                  onCheckedChange={(checked) => setNotifications({ ...notifications, promotionAlerts: checked })}
                />
              </div>

              <div className="flex items-center justify-between p-4 rounded-lg border border-gray-200">
                <div>
                  <h4 className="font-medium text-gray-900">Sanction Alerts</h4>
                  <p className="text-sm text-gray-600">Desktop notifications for new and expiring sanctions</p>
                </div>
                <Switch
                  checked={notifications.sanctionAlerts}
                  onCheckedChange={(checked) => setNotifications({ ...notifications, sanctionAlerts: checked })}
                />
              </div>

              <div className="flex items-center justify-between p-4 rounded-lg border border-gray-200">
                <div>
                  <h4 className="font-medium text-gray-900">Commendation Alerts</h4>
                  <p className="text-sm text-gray-600">Desktop notifications when commendations are issued</p>
                </div>
                <Switch
                  checked={notifications.commendationAlerts}
                  onCheckedChange={(checked) => setNotifications({ ...notifications, commendationAlerts: checked })}
                />
              </div>

              <Separator />

              {/* Future Features Note */}
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <Bell className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <h4 className="font-semibold text-blue-900 mb-2">Coming Soon (Thesis Extension)</h4>
                    <div className="space-y-2 text-sm text-blue-800">
                      <p>• Email notifications (requires network module)</p>
                      <p>• SMS alerts (requires network module)</p>
                      <p>• Weekly summary reports (requires network module)</p>
                      <p className="text-xs italic mt-2">These features will be available when networking capabilities are added in the thesis phase.</p>
                    </div>
                  </div>
                </div>
              </div>

              <Separator />

              <div className="flex justify-end">
                <Button onClick={handleSaveNotifications} className="gap-2">
                  <Save className="w-4 h-4" />
                  Save Notification Settings
                </Button>
              </div>
            </div>
          </Card>
        </TabsContent>

        {/* Security */}
        <TabsContent value="security">
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <Shield className="w-6 h-6 text-red-600" />
              <h3 className="text-lg font-semibold text-gray-900">Security Settings</h3>
            </div>

            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="sessionTimeout">Session Timeout (minutes)</Label>
                  <Input
                    id="sessionTimeout"
                    type="number"
                    value={securitySettings.sessionTimeout}
                    onChange={(e) => setSecuritySettings({ ...securitySettings, sessionTimeout: e.target.value })}
                    className="mt-1"
                  />
                  <p className="text-xs text-gray-500 mt-1">Auto-logout after inactivity</p>
                </div>
                <div>
                  <Label htmlFor="passwordExpiry">Password Expiry (days)</Label>
                  <Input
                    id="passwordExpiry"
                    type="number"
                    value={securitySettings.passwordExpiry}
                    onChange={(e) => setSecuritySettings({ ...securitySettings, passwordExpiry: e.target.value })}
                    className="mt-1"
                  />
                  <p className="text-xs text-gray-500 mt-1">Force password reset after this period</p>
                </div>
              </div>

              <Separator />

              <div className="flex items-center justify-between p-4 rounded-lg border border-gray-200">
                <div>
                  <h4 className="font-medium text-gray-900">Two-Factor Authentication</h4>
                  <p className="text-sm text-gray-600">Require 2FA for all admin logins</p>
                </div>
                <Switch
                  checked={securitySettings.twoFactorAuth}
                  onCheckedChange={(checked) => setSecuritySettings({ ...securitySettings, twoFactorAuth: checked })}
                />
              </div>

              <Separator />

              <div>
                <Label htmlFor="auditLogRetention">Audit Log Retention</Label>
                <Input
                  id="auditLogRetention"
                  value={securitySettings.auditLogRetention}
                  disabled
                  className="mt-1 max-w-xs"
                />
                <p className="text-xs text-gray-500 mt-1">Logs are retained indefinitely for compliance</p>
              </div>

              <Separator />

              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <Shield className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <h4 className="font-semibold text-red-900 mb-2">Security Best Practices</h4>
                    <div className="space-y-1 text-sm text-red-800">
                      <p>• Regularly review audit logs for suspicious activity</p>
                      <p>• Enforce strong password policies for all users</p>
                      <p>• Keep the system updated with latest security patches</p>
                      <p>• Limit admin access to authorized personnel only</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-end">
                <Button onClick={handleSaveSecurity} className="gap-2">
                  <Save className="w-4 h-4" />
                  Save Security Settings
                </Button>
              </div>
            </div>
          </Card>

          {/* Database Backup Section */}
          <Card className="p-6 mt-6">
            <div className="flex items-center gap-3 mb-6">
              <Database className="w-6 h-6 text-purple-600" />
              <h3 className="text-lg font-semibold text-gray-900">Database Management</h3>
            </div>

            <div className="space-y-4">
              <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-medium text-purple-900 mb-1">Database Backup</h4>
                    <p className="text-sm text-purple-700">Last backup: April 6, 2026 at 02:00 AM</p>
                  </div>
                  <Button variant="outline" className="gap-2">
                    <Database className="w-4 h-4" />
                    Create Backup
                  </Button>
                </div>
              </div>

              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-medium text-blue-900 mb-1">Export All Data</h4>
                    <p className="text-sm text-blue-700">Export complete database to CSV format</p>
                  </div>
                  <Button variant="outline" className="gap-2">
                    <Database className="w-4 h-4" />
                    Export Data
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}