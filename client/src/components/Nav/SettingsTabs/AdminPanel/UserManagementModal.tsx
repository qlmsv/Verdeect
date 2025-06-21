import React, { useState, useEffect } from 'react';
import { Dialog, DialogPanel, DialogTitle, Transition, TransitionChild } from '@headlessui/react';
import { SystemRoles } from 'librechat-data-provider';
import { useLocalize, useAuthContext } from '~/hooks';
import type { TDialogProps } from '~/common';

interface User {
  _id: string;
  name?: string;
  username?: string;
  email: string;
  role: SystemRoles;
  balance?: number;
  createdAt: string;
  lastLogin?: string;
}

function UserManagementModal({ open, onOpenChange }: TDialogProps) {
  const localize = useLocalize();
  const { user: currentUser } = useAuthContext();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);

  // Mock data for now - replace with actual API call
  const mockUsers: User[] = [
    {
      _id: '1',
      name: 'Администратор',
      email: 'admin@verdeect.ru',
      role: SystemRoles.ADMIN,
      balance: 1000000,
      createdAt: '2024-01-01T00:00:00Z',
      lastLogin: '2024-06-21T09:00:00Z'
    },
    {
      _id: '2', 
      name: 'Тестовый пользователь',
      email: 'user@verdeect.ru',
      role: SystemRoles.USER,
      balance: 50000,
      createdAt: '2024-02-15T00:00:00Z',
      lastLogin: '2024-06-20T15:30:00Z'
    }
  ];

  useEffect(() => {
    if (open) {
      setLoading(true);
      // Simulate API call
      setTimeout(() => {
        setUsers(mockUsers);
        setLoading(false);
      }, 500);
    }
  }, [open]);

  const handleEditUser = (user: User) => {
    setSelectedUser(user);
    setShowEditModal(true);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatBalance = (balance?: number) => {
    if (!balance) return '0';
    return balance.toLocaleString('ru-RU');
  };

  return (
    <>
      <Transition appear show={open}>
        <Dialog as="div" className="relative z-50" onClose={onOpenChange}>
          <TransitionChild
            enter="ease-out duration-200"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black opacity-50 dark:opacity-80" aria-hidden="true" />
          </TransitionChild>

          <TransitionChild
            enter="ease-out duration-200"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-100"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <div className="fixed inset-0 flex w-screen items-center justify-center p-4">
              <DialogPanel className="w-full max-w-4xl overflow-hidden rounded-xl bg-background shadow-2xl">
                <DialogTitle className="flex items-center justify-between border-b border-border-light p-6">
                  <h2 className="text-xl font-semibold text-text-primary">
                    Управление пользователями
                  </h2>
                  <button
                    type="button"
                    className="rounded-sm opacity-70 transition-opacity hover:opacity-100"
                    onClick={() => onOpenChange(false)}
                  >
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </DialogTitle>

                <div className="max-h-[70vh] overflow-auto p-6">
                  {loading ? (
                    <div className="flex items-center justify-center py-8">
                      <div className="text-text-secondary">Загрузка пользователей...</div>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full border-collapse">
                        <thead>
                          <tr className="border-b border-border-light">
                            <th className="text-left py-3 px-2 font-medium text-text-primary">Пользователь</th>
                            <th className="text-left py-3 px-2 font-medium text-text-primary">Email</th>
                            <th className="text-left py-3 px-2 font-medium text-text-primary">Роль</th>
                            <th className="text-left py-3 px-2 font-medium text-text-primary">Баланс</th>
                            <th className="text-left py-3 px-2 font-medium text-text-primary">Последний вход</th>
                            <th className="text-left py-3 px-2 font-medium text-text-primary">Действия</th>
                          </tr>
                        </thead>
                        <tbody>
                          {users.map((user) => (
                            <tr key={user._id} className="border-b border-border-light hover:bg-surface-hover">
                              <td className="py-3 px-2">
                                <div>
                                  <div className="font-medium text-text-primary">{user.name || 'Без имени'}</div>
                                  <div className="text-sm text-text-secondary">ID: {user._id}</div>
                                </div>
                              </td>
                              <td className="py-3 px-2 text-text-secondary">{user.email}</td>
                              <td className="py-3 px-2">
                                <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                                  user.role === SystemRoles.ADMIN 
                                    ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                                    : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                                }`}>
                                  {user.role === SystemRoles.ADMIN ? 'Администратор' : 'Пользователь'}
                                </span>
                              </td>
                              <td className="py-3 px-2 text-text-secondary">
                                {formatBalance(user.balance)} токенов
                              </td>
                              <td className="py-3 px-2 text-text-secondary">
                                {user.lastLogin ? formatDate(user.lastLogin) : 'Никогда'}
                              </td>
                              <td className="py-3 px-2">
                                <button
                                  onClick={() => handleEditUser(user)}
                                  className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                                  disabled={user._id === currentUser?._id}
                                >
                                  Редактировать
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </DialogPanel>
            </div>
          </TransitionChild>
        </Dialog>
      </Transition>

      {/* Edit User Modal */}
      {selectedUser && (
        <UserEditModal
          user={selectedUser}
          open={showEditModal}
          onOpenChange={setShowEditModal}
          onUserUpdated={(updatedUser) => {
            setUsers(users.map(u => u._id === updatedUser._id ? updatedUser : u));
            setShowEditModal(false);
          }}
        />
      )}
    </>
  );
}

// Simple edit modal component
function UserEditModal({ 
  user, 
  open, 
  onOpenChange, 
  onUserUpdated 
}: { 
  user: User; 
  open: boolean; 
  onOpenChange: (open: boolean) => void;
  onUserUpdated: (user: User) => void;
}) {
  const [role, setRole] = useState(user.role);
  const [balance, setBalance] = useState(user.balance?.toString() || '0');

  const handleSave = () => {
    // Here you would make an API call to update the user
    const updatedUser = {
      ...user,
      role,
      balance: parseInt(balance) || 0
    };
    onUserUpdated(updatedUser);
  };

  return (
    <Transition appear show={open}>
      <Dialog as="div" className="relative z-50" onClose={onOpenChange}>
        <TransitionChild
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black opacity-50 dark:opacity-80" aria-hidden="true" />
        </TransitionChild>

        <TransitionChild
          enter="ease-out duration-200"
          enterFrom="opacity-0 scale-95"
          enterTo="opacity-100 scale-100"
          leave="ease-in duration-100"
          leaveFrom="opacity-100 scale-100"
          leaveTo="opacity-0 scale-95"
        >
          <div className="fixed inset-0 flex w-screen items-center justify-center p-4">
            <DialogPanel className="w-full max-w-md overflow-hidden rounded-xl bg-background shadow-2xl">
              <DialogTitle className="flex items-center justify-between border-b border-border-light p-4">
                <h3 className="text-lg font-semibold text-text-primary">
                  Редактировать пользователя
                </h3>
                <button
                  type="button"
                  className="rounded-sm opacity-70 transition-opacity hover:opacity-100"
                  onClick={() => onOpenChange(false)}
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </DialogTitle>

              <div className="p-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-1">
                    Email
                  </label>
                  <input
                    type="text"
                    value={user.email}
                    disabled
                    className="w-full px-3 py-2 border border-border-medium rounded-md bg-surface-secondary text-text-secondary"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-primary mb-1">
                    Роль
                  </label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value as SystemRoles)}
                    className="w-full px-3 py-2 border border-border-medium rounded-md bg-background text-text-primary"
                  >
                    <option value={SystemRoles.USER}>Пользователь</option>
                    <option value={SystemRoles.ADMIN}>Администратор</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-primary mb-1">
                    Баланс (токены)
                  </label>
                  <input
                    type="number"
                    value={balance}
                    onChange={(e) => setBalance(e.target.value)}
                    className="w-full px-3 py-2 border border-border-medium rounded-md bg-background text-text-primary"
                    min="0"
                  />
                </div>

                <div className="flex justify-end space-x-2 pt-4">
                  <button
                    onClick={() => onOpenChange(false)}
                    className="px-4 py-2 text-sm text-text-secondary hover:text-text-primary"
                  >
                    Отмена
                  </button>
                  <button
                    onClick={handleSave}
                    className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
                  >
                    Сохранить
                  </button>
                </div>
              </div>
            </DialogPanel>
          </div>
        </TransitionChild>
      </Dialog>
    </Transition>
  );
}

export default UserManagementModal; 