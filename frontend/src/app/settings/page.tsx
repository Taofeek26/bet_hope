'use client';

import { Settings, User, Bell, Globe, Shield, Palette, Database, Save } from 'lucide-react';
import { useState } from 'react';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('general');

  return (
    <>
      <div className="content-header">
        <h1>Settings</h1>
        <p>Manage your preferences and account settings</p>
      </div>

      <div className="content-grid">
        {/* Settings Navigation */}
        <div className="col-span-3">
          <div className="card">
            <nav className="space-y-1">
              <SettingsTab
                icon={Settings}
                label="General"
                active={activeTab === 'general'}
                onClick={() => setActiveTab('general')}
              />
              <SettingsTab
                icon={Bell}
                label="Notifications"
                active={activeTab === 'notifications'}
                onClick={() => setActiveTab('notifications')}
              />
              <SettingsTab
                icon={Globe}
                label="Region & Odds"
                active={activeTab === 'region'}
                onClick={() => setActiveTab('region')}
              />
              <SettingsTab
                icon={Palette}
                label="Appearance"
                active={activeTab === 'appearance'}
                onClick={() => setActiveTab('appearance')}
              />
              <SettingsTab
                icon={Database}
                label="Data & Privacy"
                active={activeTab === 'privacy'}
                onClick={() => setActiveTab('privacy')}
              />
            </nav>
          </div>
        </div>

        {/* Settings Content */}
        <div className="col-span-9">
          {activeTab === 'general' && <GeneralSettings />}
          {activeTab === 'notifications' && <NotificationSettings />}
          {activeTab === 'region' && <RegionSettings />}
          {activeTab === 'appearance' && <AppearanceSettings />}
          {activeTab === 'privacy' && <PrivacySettings />}
        </div>
      </div>
    </>
  );
}

function SettingsTab({ icon: Icon, label, active, onClick }: {
  icon: any;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`tab-btn w-full ${active ? 'active' : ''}`}
    >
      <Icon className="w-4 h-4" />
      <span className="tab-label">{label}</span>
    </button>
  );
}

function GeneralSettings() {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-icon">
          <Settings className="w-5 h-5" />
        </div>
        <div>
          <h2 className="card-title">General Settings</h2>
          <p className="card-desc">Basic app preferences</p>
        </div>
      </div>

      <div className="space-y-6">
        <SettingItem
          label="Default View"
          description="Choose your default dashboard view"
        >
          <select className="input select w-48">
            <option>Dashboard</option>
            <option>Predictions</option>
            <option>Matches</option>
          </select>
        </SettingItem>

        <SettingItem
          label="Predictions Per Page"
          description="Number of predictions to show per page"
        >
          <select className="input select w-48">
            <option>10</option>
            <option>25</option>
            <option>50</option>
          </select>
        </SettingItem>

        <SettingItem
          label="Auto-refresh"
          description="Automatically refresh data every 5 minutes"
        >
          <Toggle defaultChecked />
        </SettingItem>

        <div className="pt-4 border-t border-border-dim">
          <button className="btn btn-primary">
            <Save className="w-4 h-4" />
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}

function NotificationSettings() {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-icon">
          <Bell className="w-5 h-5" />
        </div>
        <div>
          <h2 className="card-title">Notification Settings</h2>
          <p className="card-desc">Manage how you receive updates</p>
        </div>
      </div>

      <div className="space-y-6">
        <SettingItem label="Match Notifications" description="Get notified when your favorite team plays">
          <Toggle defaultChecked />
        </SettingItem>
        <SettingItem label="Prediction Alerts" description="Receive alerts for new high-confidence predictions">
          <Toggle defaultChecked />
        </SettingItem>
        <SettingItem label="Value Bet Alerts" description="Get notified when value bets are detected">
          <Toggle defaultChecked />
        </SettingItem>
        <SettingItem label="Email Digest" description="Receive daily email summaries">
          <Toggle />
        </SettingItem>

        <div className="pt-4 border-t border-border-dim">
          <button className="btn btn-primary">
            <Save className="w-4 h-4" />
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}

function RegionSettings() {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-icon">
          <Globe className="w-5 h-5" />
        </div>
        <div>
          <h2 className="card-title">Region & Odds Format</h2>
          <p className="card-desc">Set your regional preferences</p>
        </div>
      </div>

      <div className="space-y-6">
        <SettingItem label="Timezone" description="Display times in your local timezone">
          <select className="input select w-48">
            <option>UTC</option>
            <option>GMT</option>
            <option>EST</option>
            <option>PST</option>
            <option>CET</option>
          </select>
        </SettingItem>

        <SettingItem label="Odds Format" description="How odds are displayed">
          <select className="input select w-48">
            <option>Decimal (1.50)</option>
            <option>Fractional (1/2)</option>
            <option>American (+150)</option>
          </select>
        </SettingItem>

        <SettingItem label="Date Format" description="How dates are displayed">
          <select className="input select w-48">
            <option>DD/MM/YYYY</option>
            <option>MM/DD/YYYY</option>
            <option>YYYY-MM-DD</option>
          </select>
        </SettingItem>

        <div className="pt-4 border-t border-border-dim">
          <button className="btn btn-primary">
            <Save className="w-4 h-4" />
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}

function AppearanceSettings() {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-icon">
          <Palette className="w-5 h-5" />
        </div>
        <div>
          <h2 className="card-title">Appearance</h2>
          <p className="card-desc">Customize the look and feel</p>
        </div>
      </div>

      <div className="space-y-6">
        <SettingItem label="Theme" description="Choose your preferred theme">
          <select className="input select w-48">
            <option>Dark (Default)</option>
            <option>Light</option>
            <option>System</option>
          </select>
        </SettingItem>

        <SettingItem label="Compact Mode" description="Use smaller spacing and fonts">
          <Toggle />
        </SettingItem>

        <SettingItem label="Show Animations" description="Enable UI animations">
          <Toggle defaultChecked />
        </SettingItem>

        <div className="pt-4 border-t border-border-dim">
          <button className="btn btn-primary">
            <Save className="w-4 h-4" />
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}

function PrivacySettings() {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-icon">
          <Shield className="w-5 h-5" />
        </div>
        <div>
          <h2 className="card-title">Data & Privacy</h2>
          <p className="card-desc">Control your data and privacy settings</p>
        </div>
      </div>

      <div className="space-y-6">
        <SettingItem label="Analytics" description="Help improve the app by sharing anonymous usage data">
          <Toggle defaultChecked />
        </SettingItem>

        <SettingItem label="Save Prediction History" description="Keep a history of your viewed predictions">
          <Toggle defaultChecked />
        </SettingItem>

        <div className="pt-4 border-t border-border-dim">
          <button className="btn btn-secondary">
            Clear Local Data
          </button>
        </div>
      </div>
    </div>
  );
}

function SettingItem({ label, description, children }: {
  label: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <div className="font-medium text-text">{label}</div>
        <div className="text-sm text-text-muted">{description}</div>
      </div>
      {children}
    </div>
  );
}

function Toggle({ defaultChecked = false }: { defaultChecked?: boolean }) {
  return (
    <label className="relative inline-flex cursor-pointer">
      <input type="checkbox" defaultChecked={defaultChecked} className="sr-only peer" />
      <div className="w-11 h-6 bg-border rounded-full peer peer-checked:bg-brand peer-focus:ring-2 peer-focus:ring-brand/30 transition-colors">
        <div className="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
      </div>
    </label>
  );
}
