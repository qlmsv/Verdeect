import React, { useState } from 'react';
import { SystemRoles } from 'librechat-data-provider';
import { useAuthContext, useLocalize } from '~/hooks';
import UserManagementModal from './UserManagementModal';
import BalanceManagementModal from './BalanceManagementModal';
import SystemStatsModal from './SystemStatsModal';

function AdminPanel() {
  const { user } = useAuthContext();
  const localize = useLocalize();
  
  // States for modal windows
  const [showUserManagement, setShowUserManagement] = useState(false);
  const [showBalanceManagement, setShowBalanceManagement] = useState(false);
  const [showSystemStats, setShowSystemStats] = useState(false);

  // Security check - only show for ADMIN users
  if (user?.role !== SystemRoles.ADMIN) {
    return null;
  }

  return (
    <>
      <div className="flex flex-col gap-3 p-1 text-sm text-text-primary">
        <div className="pb-3">
          <h3 className="text-lg font-medium text-text-primary">
            {localize('com_nav_setting_admin_panel')}
          </h3>
          <p className="mt-2 text-sm text-text-secondary">
            Панель управления для администраторов. Здесь можно управлять пользователями, балансами и системными настройками.
          </p>
        </div>
        
        <div className="space-y-4">
          <div className="rounded-lg border border-border-medium p-4">
            <h4 className="font-medium text-text-primary">Управление пользователями</h4>
            <p className="mt-1 text-sm text-text-secondary">
              Просмотр списка пользователей, изменение ролей и управление доступом.
            </p>
            <button 
              onClick={() => setShowUserManagement(true)}
              className="mt-2 rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 transition-colors"
            >
              Открыть
            </button>
          </div>

          <div className="rounded-lg border border-border-medium p-4">
            <h4 className="font-medium text-text-primary">Управление балансами</h4>
            <p className="mt-1 text-sm text-text-secondary">
              Пополнение и управление балансами пользователей.
            </p>
            <button 
              onClick={() => setShowBalanceManagement(true)}
              className="mt-2 rounded bg-green-600 px-3 py-1 text-sm text-white hover:bg-green-700 transition-colors"
            >
              Открыть
            </button>
          </div>

          <div className="rounded-lg border border-border-medium p-4">
            <h4 className="font-medium text-text-primary">Системная статистика</h4>
            <p className="mt-1 text-sm text-text-secondary">
              Просмотр статистики использования системы и мониторинг.
            </p>
            <button 
              onClick={() => setShowSystemStats(true)}
              className="mt-2 rounded bg-purple-600 px-3 py-1 text-sm text-white hover:bg-purple-700 transition-colors"
            >
              Открыть
            </button>
          </div>
        </div>
      </div>

      {/* Modal Windows */}
      <UserManagementModal 
        open={showUserManagement} 
        onOpenChange={setShowUserManagement} 
      />
      <BalanceManagementModal 
        open={showBalanceManagement} 
        onOpenChange={setShowBalanceManagement} 
      />
      <SystemStatsModal 
        open={showSystemStats} 
        onOpenChange={setShowSystemStats} 
      />
    </>
  );
}

export default AdminPanel; 