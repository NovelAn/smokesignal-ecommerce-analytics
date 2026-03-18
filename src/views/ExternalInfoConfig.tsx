/**
 * 场外信息配置视图
 * External Information Configuration View
 *
 * 管理客户的线下消费和私域沟通记录
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  Search,
  Filter,
  Upload,
  MessageCircle,
  CreditCard,
  Calendar,
  MapPin,
  MoreVertical,
  Edit2,
  Trash2,
  X,
  AlertCircle,
  CheckCircle,
  Download,
  ChevronLeft,
  ChevronRight,
  RefreshCw
} from 'lucide-react';
import { NotionCard } from '../components/common/NotionCard';
import { NotionTag } from '../components/common/NotionTag';
import { apiClient, APIError } from '../api/client';
import {
  ExternalRecord,
  ExternalRecordType,
  ExternalRecordsStats,
  BatchImportResult
} from '../types';

// 预定义渠道选项
const CHANNEL_OPTIONS = [
  '微信', '电话', '企业微信',
  '北京SKP', '上海国金', '广州太古汇', '深圳万象城', '杭州大厦',
  '成都IFS', '南京德基', '武汉国际', '西安赛格', '其他'
];

// 品类选项
const CATEGORY_OPTIONS = [
  'Pipes', 'Lighters', 'Cigars', 'Accessories', 'Apparel', 'Leather Goods', '其他'
];

const ExternalInfoConfig: React.FC = () => {
  // 数据状态
  const [records, setRecords] = useState<ExternalRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<ExternalRecordsStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 筛选状态
  const [search, setSearch] = useState('');
  const [recordType, setRecordType] = useState<ExternalRecordType | ''>('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  // 弹窗状态
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [editingRecord, setEditingRecord] = useState<ExternalRecord | null>(null);
  const [deletingRecord, setDeletingRecord] = useState<ExternalRecord | null>(null);

  // 导入结果
  const [importResult, setImportResult] = useState<BatchImportResult | null>(null);

  // 加载数据
  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // 并行加载记录和统计
      const [recordsRes, statsRes] = await Promise.all([
        apiClient.getExternalRecords({
          search: search || undefined,
          record_type: recordType || undefined,
          limit: pageSize,
          offset: (currentPage - 1) * pageSize
        }),
        apiClient.getExternalRecordsStats()
      ]);

      setRecords(recordsRes.records);
      setTotal(recordsRes.total);
      setStats(statsRes);
    } catch (err) {
      console.error('Failed to load external records:', err);
      setError(err instanceof APIError ? err.message : '加载数据失败');
    } finally {
      setIsLoading(false);
    }
  }, [search, recordType, currentPage]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 搜索处理
  const handleSearch = (value: string) => {
    setSearch(value);
    setCurrentPage(1);
  };

  // 类型筛选处理
  const handleTypeFilter = (type: ExternalRecordType | '') => {
    setRecordType(type);
    setCurrentPage(1);
  };

  // 添加记录成功
  const handleAddSuccess = () => {
    setShowAddModal(false);
    loadData();
  };

  // 编辑记录成功
  const handleEditSuccess = () => {
    setEditingRecord(null);
    loadData();
  };

  // 删除记录
  const handleDelete = async () => {
    if (!deletingRecord) return;

    try {
      await apiClient.deleteExternalRecord(deletingRecord.id);
      setDeletingRecord(null);
      loadData();
    } catch (err) {
      console.error('Failed to delete record:', err);
      setError(err instanceof APIError ? err.message : '删除失败');
    }
  };

  // 导入成功
  const handleImportSuccess = (result: BatchImportResult) => {
    setImportResult(result);
    if (result.success_count > 0) {
      loadData();
    }
  };

  // 总页数
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      {/* 标题和说明 */}
      <div>
        <h2 className="text-2xl font-serif text-notion-text mb-2">场外信息配置</h2>
        <p className="text-sm text-notion-muted">
          补充客户的线下消费和私域沟通记录，用于AI综合分析。
          场外信息不会累计到线上消费统计中。
        </p>
      </div>

      {/* 统计卡片 */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <NotionCard className="p-4">
            <div className="text-xs text-notion-muted mb-1">总记录数</div>
            <div className="text-2xl font-semibold text-notion-text">{stats.total_records}</div>
          </NotionCard>
          <NotionCard className="p-4">
            <div className="flex items-center gap-2 text-xs text-notion-muted mb-1">
              <MessageCircle size={12} />
              沟通记录
            </div>
            <div className="text-2xl font-semibold text-blue-600">{stats.communication_count}</div>
          </NotionCard>
          <NotionCard className="p-4">
            <div className="flex items-center gap-2 text-xs text-notion-muted mb-1">
              <CreditCard size={12} />
              消费记录
            </div>
            <div className="text-2xl font-semibold text-green-600">{stats.purchase_count}</div>
          </NotionCard>
          <NotionCard className="p-4">
            <div className="text-xs text-notion-muted mb-1">线下消费总额</div>
            <div className="text-2xl font-semibold text-notion-text">
              ¥{stats.total_offline_amount.toLocaleString()}
            </div>
          </NotionCard>
        </div>
      )}

      {/* 工具栏 */}
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
        <div className="flex flex-1 gap-3 w-full sm:w-auto">
          {/* 搜索框 */}
          <div className="relative flex-1 max-w-xs">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-notion-muted" />
            <input
              type="text"
              placeholder="搜索客户昵称..."
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm border border-notion-border rounded-md
                       bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            {search && (
              <button
                onClick={() => handleSearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-notion-muted hover:text-notion-text"
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* 类型筛选 */}
          <select
            value={recordType}
            onChange={(e) => handleTypeFilter(e.target.value as ExternalRecordType | '')}
            className="px-3 py-2 text-sm border border-notion-border rounded-md
                     bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">全部类型</option>
            <option value="communication">沟通记录</option>
            <option value="purchase">消费记录</option>
          </select>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setShowImportModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-notion-border
                     rounded-md hover:bg-notion-hover transition-colors"
          >
            <Upload size={16} />
            批量导入
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 text-white
                     rounded-md hover:bg-blue-700 transition-colors"
          >
            <Plus size={16} />
            添加记录
          </button>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
          <AlertCircle size={16} />
          {error}
          <button onClick={() => setError(null)} className="ml-auto">
            <X size={14} />
          </button>
        </div>
      )}

      {/* 数据表格 */}
      <NotionCard className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-notion-sidebar border-b border-notion-border">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-notion-muted">客户</th>
                <th className="px-4 py-3 text-left font-medium text-notion-muted">类型</th>
                <th className="px-4 py-3 text-left font-medium text-notion-muted">日期</th>
                <th className="px-4 py-3 text-left font-medium text-notion-muted">渠道/门店</th>
                <th className="px-4 py-3 text-left font-medium text-notion-muted">内容/金额</th>
                <th className="px-4 py-3 text-left font-medium text-notion-muted">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-notion-border">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-notion-muted">
                    <RefreshCw size={20} className="animate-spin mx-auto mb-2" />
                    加载中...
                  </td>
                </tr>
              ) : records.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-notion-muted">
                    暂无场外记录，点击"添加记录"开始录入
                  </td>
                </tr>
              ) : (
                records.map((record) => (
                  <tr key={record.id} className="hover:bg-notion-hover/50 transition-colors">
                    <td className="px-4 py-3">
                      <span className="font-medium text-notion-text">{record.user_nick}</span>
                    </td>
                    <td className="px-4 py-3">
                      <NotionTag
                        variant={record.record_type === 'communication' ? 'blue' : 'green'}
                      >
                        {record.record_type === 'communication' ? '沟通' : '消费'}
                      </NotionTag>
                    </td>
                    <td className="px-4 py-3 text-notion-muted">
                      {record.record_date}
                    </td>
                    <td className="px-4 py-3 text-notion-muted">
                      {record.channel || '-'}
                    </td>
                    <td className="px-4 py-3">
                      {record.record_type === 'purchase' ? (
                        <div>
                          <span className="font-medium text-green-600">
                            ¥{(record.amount || 0).toLocaleString()}
                          </span>
                          {record.category && (
                            <span className="ml-2 text-xs text-notion-muted">
                              ({record.category})
                            </span>
                          )}
                        </div>
                      ) : (
                        <div className="max-w-xs truncate text-notion-muted">
                          {record.content || '-'}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setEditingRecord(record)}
                          className="p-1.5 text-notion-muted hover:text-blue-600 hover:bg-blue-50 rounded"
                          title="编辑"
                        >
                          <Edit2 size={14} />
                        </button>
                        <button
                          onClick={() => setDeletingRecord(record)}
                          className="p-1.5 text-notion-muted hover:text-red-600 hover:bg-red-50 rounded"
                          title="删除"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-notion-border">
            <div className="text-sm text-notion-muted">
              共 {total} 条记录
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="p-1.5 border border-notion-border rounded hover:bg-notion-hover
                         disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="text-sm text-notion-muted">
                {currentPage} / {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="p-1.5 border border-notion-border rounded hover:bg-notion-hover
                         disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </NotionCard>

      {/* 添加/编辑弹窗 */}
      {(showAddModal || editingRecord) && (
        <RecordModal
          record={editingRecord}
          channelOptions={CHANNEL_OPTIONS}
          categoryOptions={CATEGORY_OPTIONS}
          onSuccess={editingRecord ? handleEditSuccess : handleAddSuccess}
          onClose={() => {
            setShowAddModal(false);
            setEditingRecord(null);
          }}
        />
      )}

      {/* 删除确认弹窗 */}
      {deletingRecord && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 rounded-full">
                <AlertCircle size={20} className="text-red-600" />
              </div>
              <div>
                <h3 className="font-medium text-notion-text">确认删除</h3>
                <p className="text-sm text-notion-muted">
                  确定要删除这条记录吗？此操作无法撤销。
                </p>
              </div>
            </div>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeletingRecord(null)}
                className="px-4 py-2 text-sm border border-notion-border rounded-md
                         hover:bg-notion-hover transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleDelete}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded-md
                         hover:bg-red-700 transition-colors"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 批量导入弹窗 */}
      {showImportModal && (
        <ImportModal
          templateUrl={apiClient.getExternalRecordsTemplate()}
          onImport={handleImportSuccess}
          onClose={() => {
            setShowImportModal(false);
            setImportResult(null);
          }}
          importResult={importResult}
        />
      )}
    </div>
  );
};

// ============================================
// 记录弹窗组件
// ============================================

interface RecordModalProps {
  record: ExternalRecord | null;
  channelOptions: string[];
  categoryOptions: string[];
  onSuccess: () => void;
  onClose: () => void;
}

const RecordModal: React.FC<RecordModalProps> = ({
  record,
  channelOptions,
  categoryOptions,
  onSuccess,
  onClose
}) => {
  const isEdit = !!record;
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 表单状态
  const [formData, setFormData] = useState({
    user_nick: record?.user_nick || '',
    record_type: (record?.record_type || 'communication') as ExternalRecordType,
    record_date: record?.record_date || new Date().toISOString().split('T')[0],
    channel: record?.channel || '',
    content: record?.content || '',
    notes: record?.notes || '',
    amount: record?.amount?.toString() || '',
    category: record?.category || ''
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const payload = {
        user_nick: formData.user_nick,
        record_type: formData.record_type,
        record_date: formData.record_date,
        channel: formData.channel || null,
        content: formData.content || null,
        notes: formData.notes || null,
        amount: formData.record_type === 'purchase' && formData.amount
          ? parseFloat(formData.amount)
          : null,
        category: formData.record_type === 'purchase' ? formData.category || null : null
      };

      if (isEdit) {
        await apiClient.updateExternalRecord(record.id, payload);
      } else {
        await apiClient.createExternalRecord(payload);
      }

      onSuccess();
    } catch (err) {
      console.error('Failed to save record:', err);
      setError(err instanceof APIError ? err.message : '保存失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-notion-text">
            {isEdit ? '编辑记录' : '添加记录'}
          </h3>
          <button onClick={onClose} className="text-notion-muted hover:text-notion-text">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          {/* 客户昵称 */}
          <div>
            <label className="block text-sm font-medium text-notion-text mb-1">
              客户昵称 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={formData.user_nick}
              onChange={(e) => setFormData({ ...formData, user_nick: e.target.value })}
              className="w-full px-3 py-2 border border-notion-border rounded-md
                       focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="输入客户昵称"
            />
          </div>

          {/* 记录类型 */}
          <div>
            <label className="block text-sm font-medium text-notion-text mb-1">
              记录类型 <span className="text-red-500">*</span>
            </label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="record_type"
                  value="communication"
                  checked={formData.record_type === 'communication'}
                  onChange={() => setFormData({ ...formData, record_type: 'communication' })}
                  className="text-blue-600"
                />
                <MessageCircle size={16} />
                <span>沟通记录</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="record_type"
                  value="purchase"
                  checked={formData.record_type === 'purchase'}
                  onChange={() => setFormData({ ...formData, record_type: 'purchase' })}
                  className="text-blue-600"
                />
                <CreditCard size={16} />
                <span>消费记录</span>
              </label>
            </div>
          </div>

          {/* 日期 */}
          <div>
            <label className="block text-sm font-medium text-notion-text mb-1">
              日期 <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              required
              value={formData.record_date}
              onChange={(e) => setFormData({ ...formData, record_date: e.target.value })}
              className="w-full px-3 py-2 border border-notion-border rounded-md
                       focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* 渠道 */}
          <div>
            <label className="block text-sm font-medium text-notion-text mb-1">渠道/门店</label>
            <select
              value={formData.channel}
              onChange={(e) => setFormData({ ...formData, channel: e.target.value })}
              className="w-full px-3 py-2 border border-notion-border rounded-md
                       focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">选择渠道...</option>
              {channelOptions.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </div>

          {/* 消费记录专用字段 */}
          {formData.record_type === 'purchase' && (
            <>
              <div>
                <label className="block text-sm font-medium text-notion-text mb-1">
                  消费金额 <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  value={formData.amount}
                  onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                  className="w-full px-3 py-2 border border-notion-border rounded-md
                           focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="输入消费金额"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-notion-text mb-1">商品品类</label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full px-3 py-2 border border-notion-border rounded-md
                           focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">选择品类...</option>
                  {categoryOptions.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>
            </>
          )}

          {/* 内容描述 */}
          {formData.record_type === 'communication' && (
            <div>
              <label className="block text-sm font-medium text-notion-text mb-1">沟通内容</label>
              <textarea
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                className="w-full px-3 py-2 border border-notion-border rounded-md
                         focus:outline-none focus:ring-1 focus:ring-blue-500"
                rows={3}
                placeholder="描述沟通的主要内容..."
              />
            </div>
          )}

          {/* 备注 */}
          <div>
            <label className="block text-sm font-medium text-notion-text mb-1">备注</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="w-full px-3 py-2 border border-notion-border rounded-md
                       focus:outline-none focus:ring-1 focus:ring-blue-500"
              rows={2}
              placeholder="添加备注..."
            />
          </div>

          {/* 按钮 */}
          <div className="flex gap-3 justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm border border-notion-border rounded-md
                       hover:bg-notion-hover transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md
                       hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {isSubmitting ? '保存中...' : (isEdit ? '保存' : '添加')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ============================================
// 导入弹窗组件
// ============================================

interface ImportModalProps {
  templateUrl: string;
  onImport: (result: BatchImportResult) => void;
  onClose: () => void;
  importResult: BatchImportResult | null;
}

const ImportModal: React.FC<ImportModalProps> = ({
  templateUrl,
  onImport,
  onClose,
  importResult
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.csv')) {
        setError('请选择 CSV 文件');
        return;
      }
      setFile(selectedFile);
      setError(null);
    }
  };

  const handleImport = async () => {
    if (!file) return;

    setIsImporting(true);
    setError(null);

    try {
      const result = await apiClient.importExternalRecords(file, 'admin');
      onImport(result);
    } catch (err) {
      console.error('Import failed:', err);
      setError(err instanceof APIError ? err.message : '导入失败');
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-notion-text">批量导入</h3>
          <button onClick={onClose} className="text-notion-muted hover:text-notion-text">
            <X size={20} />
          </button>
        </div>

        {importResult ? (
          // 显示导入结果
          <div className="space-y-4">
            <div className={`p-4 rounded-lg ${
              importResult.failed_count === 0 ? 'bg-green-50' : 'bg-yellow-50'
            }`}>
              <div className="flex items-center gap-2 mb-2">
                {importResult.failed_count === 0 ? (
                  <CheckCircle className="text-green-600" size={20} />
                ) : (
                  <AlertCircle className="text-yellow-600" size={20} />
                )}
                <span className="font-medium">导入完成</span>
              </div>
              <p className="text-sm text-notion-muted">
                成功导入 <span className="font-medium text-green-600">{importResult.success_count}</span> 条记录
                {importResult.failed_count > 0 && (
                  <span>，失败 <span className="font-medium text-red-600">{importResult.failed_count}</span> 条</span>
                )}
              </p>
            </div>

            {(importResult.errors.length > 0 || (importResult.parse_errors?.length || 0) > 0) && (
              <div className="bg-red-50 p-3 rounded-lg">
                <p className="text-sm font-medium text-red-700 mb-2">错误信息：</p>
                <ul className="text-xs text-red-600 space-y-1">
                  {[...importResult.errors, ...(importResult.parse_errors || [])].slice(0, 5).map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                  {[...importResult.errors, ...(importResult.parse_errors || [])].length > 5 && (
                    <li>...还有 {[...importResult.errors, ...(importResult.parse_errors || [])].length - 5} 条错误</li>
                  )}
                </ul>
              </div>
            )}

            <div className="flex justify-end">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md
                         hover:bg-blue-700 transition-colors"
              >
                完成
              </button>
            </div>
          </div>
        ) : (
          // 导入表单
          <div className="space-y-4">
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                <AlertCircle size={16} />
                {error}
              </div>
            )}

            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-sm text-blue-700 mb-2">
                CSV 文件格式要求：
              </p>
              <ul className="text-xs text-blue-600 space-y-1">
                <li>• 必须包含表头：user_nick, record_type, record_date</li>
                <li>• record_type 必须是 communication 或 purchase</li>
                <li>• record_date 格式：YYYY-MM-DD</li>
                <li>• 可选字段：channel, content, notes, amount, category</li>
              </ul>
              <a
                href={templateUrl}
                download="external_records_template.csv"
                className="inline-flex items-center gap-1 mt-3 text-sm text-blue-700 hover:text-blue-800"
              >
                <Download size={14} />
                下载导入模板
              </a>
            </div>

            <div>
              <label className="block text-sm font-medium text-notion-text mb-2">
                选择 CSV 文件
              </label>
              <input
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="w-full text-sm file:mr-4 file:py-2 file:px-4
                         file:rounded-md file:border-0
                         file:text-sm file:font-medium
                         file:bg-blue-50 file:text-blue-700
                         hover:file:bg-blue-100"
              />
              {file && (
                <p className="mt-2 text-sm text-notion-muted">
                  已选择: {file.name}
                </p>
              )}
            </div>

            <div className="flex gap-3 justify-end">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm border border-notion-border rounded-md
                         hover:bg-notion-hover transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleImport}
                disabled={!file || isImporting}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md
                         hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {isImporting ? '导入中...' : '开始导入'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ExternalInfoConfig;
