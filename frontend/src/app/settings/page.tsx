'use client';

import { Settings, Bell, Globe, Shield, Palette, Trash2, Check } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useSettings, AppSettings } from '@/contexts/SettingsContext';
import { readPredictionHistory, clearPredictionHistory } from '@/hooks/usePredictionHistory';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('general');

  return (
    <>
      <div className="content-header">
        <h1>Settings</h1>
        <p>Manage your preferences — changes apply immediately</p>
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
                icon={Shield}
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

// Flashes "Saved" next to a control right after it changes — settings
// apply immediately (no separate save step to forget to click), this is
// just visible confirmation that it actually happened.
function useSavedFlash(): [boolean, () => void] {
  const [saved, setSaved] = useState(false);
  const flash = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };
  return [saved, flash];
}

function SavedBadge({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <span className="inline-flex items-center gap-1 text-xs text-brand ml-2">
      <Check className="w-3 h-3" /> Saved
    </span>
  );
}

function GeneralSettings() {
  const { settings, updateSetting } = useSettings();
  const [saved, flash] = useSavedFlash();

  const set = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    updateSetting(key, value);
    flash();
  };

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
        <SavedBadge show={saved} />
      </div>

      <div className="space-y-6">
        <SettingItem
          label="Default View"
          description="Which page loads when you open the app"
        >
          <select
            className="input select w-48"
            value={settings.defaultView}
            onChange={(e) => set('defaultView', e.target.value as AppSettings['defaultView'])}
          >
            <option value="dashboard">Dashboard</option>
            <option value="predictions">Predictions</option>
            <option value="matches">Matches</option>
          </select>
        </SettingItem>

        <SettingItem
          label="Predictions Per Page"
          description="Number of predictions to show per page on the Predictions tab"
        >
          <select
            className="input select w-48"
            value={settings.predictionsPerPage}
            onChange={(e) => set('predictionsPerPage', Number(e.target.value) as AppSettings['predictionsPerPage'])}
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </SettingItem>

        <SettingItem
          label="Auto-refresh"
          description="Automatically poll for new live scores, picks, and predictions in the background"
        >
          <Toggle checked={settings.autoRefresh} onChange={(v) => set('autoRefresh', v)} />
        </SettingItem>
      </div>
    </div>
  );
}

function NotificationSettings() {
  const { settings, updateSetting } = useSettings();
  const [saved, flash] = useSavedFlash();
  const [permission, setPermission] = useState<NotificationPermission | 'unsupported'>('default');

  useEffect(() => {
    if (typeof window !== 'undefined' && 'Notification' in window) {
      setPermission(Notification.permission);
    } else {
      setPermission('unsupported');
    }
  }, []);

  const set = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    updateSetting(key, value);
    flash();
    if (value === true && typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().then(setPermission);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-icon">
          <Bell className="w-5 h-5" />
        </div>
        <div>
          <h2 className="card-title">Notification Settings</h2>
          <p className="card-desc">
            Browser notifications while this tab is open — there's no email or push
            infrastructure behind this app, so alerts only fire live, in-session
          </p>
        </div>
        <SavedBadge show={saved} />
      </div>

      {permission === 'unsupported' && (
        <p className="text-xs text-text-muted mb-4">Your browser doesn't support notifications.</p>
      )}
      {permission === 'denied' && (
        <p className="text-xs text-red-400 mb-4">
          Notifications are blocked for this site in your browser settings — these toggles won't
          do anything until you allow them there.
        </p>
      )}

      <div className="space-y-6">
        <SettingItem label="Match Live Alerts" description="Get notified the moment a match goes live">
          <Toggle checked={settings.matchNotifications} onChange={(v) => set('matchNotifications', v)} />
        </SettingItem>
        <SettingItem label="Prediction Alerts" description="Get notified when a new high-confidence pick appears">
          <Toggle checked={settings.predictionAlerts} onChange={(v) => set('predictionAlerts', v)} />
        </SettingItem>
        <SettingItem label="Value Bet Alerts" description="Get notified when a new value bet is detected">
          <Toggle checked={settings.valueBetAlerts} onChange={(v) => set('valueBetAlerts', v)} />
        </SettingItem>
      </div>
    </div>
  );
}

function RegionSettings() {
  const { settings, updateSetting } = useSettings();
  const [saved, flash] = useSavedFlash();

  const set = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    updateSetting(key, value);
    flash();
  };

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
        <SavedBadge show={saved} />
      </div>

      <div className="space-y-6">
        <SettingItem label="Timezone" description="Used for kickoff times shown across the app">
          <select
            className="input select w-48"
            value={settings.timezone}
            onChange={(e) => set('timezone', e.target.value)}
          >
            <option value="local">Local (Auto-detect)</option>
            <option value="UTC">UTC</option>
            <option value="Europe/London">GMT</option>
            <option value="America/New_York">EST</option>
            <option value="America/Los_Angeles">PST</option>
            <option value="Europe/Paris">CET</option>
          </select>
        </SettingItem>

        <SettingItem label="Odds Format" description="How odds are displayed on Value Bets">
          <select
            className="input select w-48"
            value={settings.oddsFormat}
            onChange={(e) => set('oddsFormat', e.target.value as AppSettings['oddsFormat'])}
          >
            <option value="decimal">Decimal (1.50)</option>
            <option value="fractional">Fractional (1/2)</option>
            <option value="american">American (+150)</option>
          </select>
        </SettingItem>

        <SettingItem label="Date Format" description="How dates are displayed on the Matches tab">
          <select
            className="input select w-48"
            value={settings.dateFormat}
            onChange={(e) => set('dateFormat', e.target.value as AppSettings['dateFormat'])}
          >
            <option value="DD/MM/YYYY">DD/MM/YYYY</option>
            <option value="MM/DD/YYYY">MM/DD/YYYY</option>
            <option value="YYYY-MM-DD">YYYY-MM-DD</option>
          </select>
        </SettingItem>
      </div>
    </div>
  );
}

function AppearanceSettings() {
  const { settings, updateSetting } = useSettings();
  const [saved, flash] = useSavedFlash();

  const set = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    updateSetting(key, value);
    flash();
  };

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
        <SavedBadge show={saved} />
      </div>

      <div className="space-y-6">
        <SettingItem label="Theme" description="Choose your preferred theme">
          <select
            className="input select w-48"
            value={settings.theme}
            onChange={(e) => set('theme', e.target.value as AppSettings['theme'])}
          >
            <option value="dark">Dark (Default)</option>
            <option value="light">Light</option>
            <option value="system">System</option>
          </select>
        </SettingItem>

        <SettingItem label="Compact Mode" description="Use smaller spacing and fonts">
          <Toggle checked={settings.compactMode} onChange={(v) => set('compactMode', v)} />
        </SettingItem>

        <SettingItem label="Show Animations" description="Enable UI transitions and motion">
          <Toggle checked={settings.showAnimations} onChange={(v) => set('showAnimations', v)} />
        </SettingItem>
      </div>
    </div>
  );
}

function PrivacySettings() {
  const { settings, updateSetting, resetSettings } = useSettings();
  const [saved, flash] = useSavedFlash();
  const [historyCount, setHistoryCount] = useState(0);
  const [cleared, setCleared] = useState(false);

  useEffect(() => {
    setHistoryCount(readPredictionHistory().length);
  }, []);

  const set = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    updateSetting(key, value);
    flash();
  };

  const handleClearData = () => {
    clearPredictionHistory();
    resetSettings();
    localStorage.removeItem('token');
    localStorage.removeItem('bethope_active_task_ids');
    setHistoryCount(0);
    setCleared(true);
    setTimeout(() => window.location.reload(), 800);
  };

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
        <SavedBadge show={saved} />
      </div>

      <div className="space-y-6">
        <SettingItem
          label="Save Prediction History"
          description={`Remember predictions you've generated AI analysis for (${historyCount} saved locally)`}
        >
          <Toggle checked={settings.savePredictionHistory} onChange={(v) => set('savePredictionHistory', v)} />
        </SettingItem>

        <div className="pt-4 border-t border-border-dim">
          <button onClick={handleClearData} className="btn btn-secondary" disabled={cleared}>
            <Trash2 className="w-4 h-4" />
            {cleared ? 'Cleared — reloading...' : 'Clear Local Data'}
          </button>
          <p className="text-xs text-text-muted mt-2">
            Resets all settings to defaults, clears prediction history and your admin sign-in, then reloads.
          </p>
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

function Toggle({ checked, onChange }: { checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <label className="relative inline-flex cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="sr-only peer"
      />
      <div className="w-11 h-6 bg-border rounded-full peer peer-checked:bg-brand peer-focus:ring-2 peer-focus:ring-brand/30 transition-colors">
        <div className="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
      </div>
    </label>
  );
}
