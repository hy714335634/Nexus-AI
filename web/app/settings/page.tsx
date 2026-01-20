'use client';

import { useState } from 'react';
import { Header } from '@/components/layout';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Badge } from '@/components/ui';
import { toast } from 'sonner';
import {
  Settings,
  User,
  Key,
  Bell,
  Palette,
  Globe,
  Shield,
  Save,
  ExternalLink,
} from 'lucide-react';

export default function SettingsPage() {
  const [apiBaseUrl, setApiBaseUrl] = useState(process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000');
  const [notifications, setNotifications] = useState({
    buildComplete: true,
    buildFailed: true,
    agentInvoked: false,
  });

  const handleSave = () => {
    // In real app, this would save to backend/localStorage
    toast.success('设置已保存');
  };

  return (
    <div className="page-container">
      <Header
        title="设置"
        description="管理您的账户和应用偏好"
      />

      <div className="page-content max-w-3xl">
        {/* Profile Settings */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="w-5 h-5 text-gray-500" />
              个人信息
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">用户名</label>
              <Input placeholder="您的用户名" defaultValue="admin" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">邮箱</label>
              <Input type="email" placeholder="your@email.com" defaultValue="admin@example.com" />
            </div>
          </CardContent>
        </Card>

        {/* API Configuration */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="w-5 h-5 text-gray-500" />
              API 配置
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">API 基础 URL</label>
              <Input
                placeholder="http://localhost:8000"
                value={apiBaseUrl}
                onChange={(e) => setApiBaseUrl(e.target.value)}
              />
              <p className="text-xs text-gray-500 mt-1">
                Nexus AI 后端服务地址
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">API 密钥</label>
              <Input type="password" placeholder="sk-..." />
              <p className="text-xs text-gray-500 mt-1">
                用于身份验证的 API 密钥（如果需要）
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Notification Settings */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="w-5 h-5 text-gray-500" />
              通知设置
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <NotificationToggle
              label="构建完成通知"
              description="当 Agent 构建完成时发送通知"
              checked={notifications.buildComplete}
              onChange={(checked) => setNotifications({ ...notifications, buildComplete: checked })}
            />
            <NotificationToggle
              label="构建失败通知"
              description="当 Agent 构建失败时发送通知"
              checked={notifications.buildFailed}
              onChange={(checked) => setNotifications({ ...notifications, buildFailed: checked })}
            />
            <NotificationToggle
              label="Agent 调用通知"
              description="当 Agent 被调用时发送通知"
              checked={notifications.agentInvoked}
              onChange={(checked) => setNotifications({ ...notifications, agentInvoked: checked })}
            />
          </CardContent>
        </Card>

        {/* Appearance */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Palette className="w-5 h-5 text-gray-500" />
              外观
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-gray-900">主题</h4>
                <p className="text-sm text-gray-500">选择界面主题</p>
              </div>
              <div className="flex gap-2">
                <button className="px-4 py-2 text-sm font-medium rounded-lg bg-primary-100 text-primary-700">
                  浅色
                </button>
                <button className="px-4 py-2 text-sm font-medium rounded-lg bg-white text-gray-600 border border-gray-200 hover:bg-gray-50">
                  深色
                </button>
                <button className="px-4 py-2 text-sm font-medium rounded-lg bg-white text-gray-600 border border-gray-200 hover:bg-gray-50">
                  跟随系统
                </button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Language */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="w-5 h-5 text-gray-500" />
              语言和地区
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-gray-900">界面语言</h4>
                <p className="text-sm text-gray-500">选择界面显示语言</p>
              </div>
              <select className="px-4 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500">
                <option value="zh-CN">简体中文</option>
                <option value="en-US">English</option>
              </select>
            </div>
          </CardContent>
        </Card>

        {/* About */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-gray-500" />
              关于
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-gray-600">版本</span>
                <Badge variant="outline">v2.0.0</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600">文档</span>
                <a href="#" className="text-primary-600 hover:text-primary-700 flex items-center gap-1 text-sm">
                  查看文档 <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600">GitHub</span>
                <a href="#" className="text-primary-600 hover:text-primary-700 flex items-center gap-1 text-sm">
                  查看源码 <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Save Button */}
        <div className="flex justify-end">
          <Button onClick={handleSave}>
            <Save className="w-4 h-4" />
            保存设置
          </Button>
        </div>
      </div>
    </div>
  );
}

function NotificationToggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h4 className="font-medium text-gray-900">{label}</h4>
        <p className="text-sm text-gray-500">{description}</p>
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`relative w-12 h-6 rounded-full transition-colors ${
          checked ? 'bg-primary-600' : 'bg-gray-300'
        }`}
      >
        <span
          className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
            checked ? 'left-7' : 'left-1'
          }`}
        />
      </button>
    </div>
  );
}
