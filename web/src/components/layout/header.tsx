'use client';

import Link from 'next/link';
import { Bell, Search, Settings, User } from 'lucide-react';
import { Input } from '@/components/ui/input';

interface HeaderProps {
  title?: string;
  description?: string;
  actions?: React.ReactNode;
}

export function Header({ title, description, actions }: HeaderProps) {
  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      <div className="flex items-center gap-6">
        {title && (
          <div>
            <h1 className="text-xl font-semibold text-gray-900">{title}</h1>
            {description && <p className="text-sm text-gray-500">{description}</p>}
          </div>
        )}
      </div>

      <div className="flex items-center gap-4">
        {/* Search */}
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            placeholder="搜索..."
            className="pl-10 py-2 text-sm"
          />
        </div>

        {actions}

        {/* Notifications */}
        <button className="relative p-2 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
        </button>

        {/* Settings - Config Management */}
        <Link 
          href="/settings/config"
          className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
          title="配置管理"
        >
          <Settings className="w-5 h-5" />
        </Link>

        {/* User */}
        <button className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-100 transition-colors">
          <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
            <User className="w-4 h-4 text-primary-600" />
          </div>
        </button>
      </div>
    </header>
  );
}
