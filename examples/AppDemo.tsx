/**
 * SmokeSignal Analytics - API Demo Page
 * 简单的 API 集成演示页面
 */
import React, { useState, useEffect } from 'react';
import { api, BuyerListResponse, ActionableCustomer, DashboardMetrics } from '../src/api';

function AppDemo() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<'dashboard' | 'buyers'>('dashboard');

  // Dashboard data
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [actionableCustomers, setActionableCustomers] = useState<ActionableCustomer[]>([]);

  // Buyers data
  const [buyers, setBuyers] = useState<string[]>([]);
  const [totalBuyers, setTotalBuyers] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedBuyer, setSelectedBuyer] = useState<string | null>(null);

  // Fetch dashboard data
  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [metricsData, customersData] = await Promise.all([
        api.getDashboardMetrics(),
        api.getActionableCustomers()
      ]);
      setMetrics(metricsData);
      setActionableCustomers(customersData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch dashboard data');
    }
    setLoading(false);
  };

  // Fetch buyers data
  const fetchBuyers = async (search?: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getBuyers({ limit: 100, search });
      setBuyers(data.buyers);
      setTotalBuyers(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch buyers');
    }
    setLoading(false);
  };

  // Initial load
  useEffect(() => {
    if (view === 'dashboard') {
      fetchDashboardData();
    } else {
      fetchBuyers();
    }
  }, [view]);

  // Handle search
  const handleSearch = () => {
    fetchBuyers(searchTerm);
  };

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', padding: '20px', backgroundColor: '#F7F7F5', minHeight: '100vh' }}>
      {/* Header */}
      <header style={{ marginBottom: '20px', borderBottom: '1px solid #E9E9E7', paddingBottom: '20px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold', color: '#37352F' }}>
          🔥 SmokeSignal Analytics - API Demo
        </h1>
        <p style={{ color: '#787774' }}>后端 API 集成演示页面</p>

        {/* Navigation */}
        <div style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
          <button
            onClick={() => setView('dashboard')}
            style={{
              padding: '8px 16px',
              backgroundColor: view === 'dashboard' ? '#37352F' : '#fff',
              color: view === 'dashboard' ? '#fff' : '#37352F',
              border: '1px solid #E9E9E7',
              borderRadius: '3px',
              cursor: 'pointer'
            }}
          >
            📊 Dashboard
          </button>
          <button
            onClick={() => setView('buyers')}
            style={{
              padding: '8px 16px',
              backgroundColor: view === 'buyers' ? '#37352F' : '#fff',
              color: view === 'buyers' ? '#fff' : '#37352F',
              border: '1px solid #E9E9E7',
              borderRadius: '3px',
              cursor: 'pointer'
            }}
          >
            👥 买家列表
          </button>
        </div>
      </header>

      {/* Error Message */}
      {error && (
        <div style={{
          padding: '15px',
          backgroundColor: '#FEF2F2',
          border: '1px solid #FECACA',
          borderRadius: '4px',
          color: '#991B1B',
          marginBottom: '20px'
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '40px', color: '#787774' }}>
          加载中...
        </div>
      )}

      {/* Dashboard View */}
      {view === 'dashboard' && !loading && metrics && (
        <div>
          <h2 style={{ fontSize: '18px', marginBottom: '15px', color: '#37352F' }}>Dashboard 概览</h2>

          {/* Metrics Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '30px' }}>
            <MetricCard label="总买家数" value={metrics.total_buyers.toLocaleString()} icon="👥" />
            <MetricCard label="总订单数" value={metrics.total_orders.toLocaleString()} icon="📦" />
            <MetricCard label="聊天消息总数" value={metrics.total_chats.toLocaleString()} icon="💬" />
            <MetricCard label="平均客户价值" value={`¥${metrics.avg_ltv.toFixed(0)}`} icon="💰" />
          </div>

          {/* VIP Distribution */}
          <h3 style={{ fontSize: '16px', marginBottom: '15px', color: '#37352F' }}>VIP 客户分布</h3>
          <div style={{ backgroundColor: '#fff', border: '1px solid #E9E9E7', borderRadius: '4px', padding: '20px', marginBottom: '30px' }}>
            <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
              {Object.entries(metrics.vip_distribution).map(([level, count]) => (
                <div key={level} style={{ flex: '1 1 100px', textAlign: 'center' }}>
                  <div style={{ fontSize: '12px', color: '#787774', marginBottom: '5px' }}>{level}</div>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#37352F' }}>{count}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Actionable Customers */}
          <h3 style={{ fontSize: '16px', marginBottom: '15px', color: '#37352F' }}>需关注客户 ({actionableCustomers.length})</h3>
          <div style={{ backgroundColor: '#fff', border: '1px solid #E9E9E7', borderRadius: '4px', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead style={{ backgroundColor: '#F1F1EF' }}>
                <tr>
                  <th style={{ padding: '10px', textAlign: 'left', fontSize: '12px' }}>买家昵称</th>
                  <th style={{ padding: '10px', textAlign: 'left', fontSize: '12px' }}>问题类型</th>
                  <th style={{ padding: '10px', textAlign: 'left', fontSize: '12px' }}>优先级</th>
                  <th style={{ padding: '10px', textAlign: 'left', fontSize: '12px' }}>最后活动</th>
                </tr>
              </thead>
              <tbody>
                {actionableCustomers.slice(0, 20).map((customer) => (
                  <tr key={customer.id} style={{ borderBottom: '1px solid #E9E9E7' }}>
                    <td style={{ padding: '10px', fontSize: '13px' }}>{customer.user_nick}</td>
                    <td style={{ padding: '10px', fontSize: '13px' }}>
                      <PriorityBadge type={customer.issue_type} />
                    </td>
                    <td style={{ padding: '10px', fontSize: '13px' }}>
                      <PriorityBadge type={customer.priority} />
                    </td>
                    <td style={{ padding: '10px', fontSize: '13px', color: '#787774' }}>{customer.last_active}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Buyers View */}
      {view === 'buyers' && !loading && (
        <div>
          <h2 style={{ fontSize: '18px', marginBottom: '15px', color: '#37352F' }}>买家列表 (共 {totalBuyers} 位)</h2>

          {/* Search */}
          <div style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
            <input
              type="text"
              placeholder="搜索买家昵称..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              style={{
                padding: '8px 12px',
                border: '1px solid #E9E9E7',
                borderRadius: '3px',
                fontSize: '14px',
                flex: 1,
                maxWidth: '300px'
              }}
            />
            <button
              onClick={handleSearch}
              style={{
                padding: '8px 16px',
                backgroundColor: '#37352F',
                color: '#fff',
                border: 'none',
                borderRadius: '3px',
                cursor: 'pointer'
              }}
            >
              搜索
            </button>
          </div>

          {/* Buyers List */}
          <div style={{ backgroundColor: '#fff', border: '1px solid #E9E9E7', borderRadius: '4px', maxHeight: '600px', overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead style={{ position: 'sticky', top: 0, backgroundColor: '#F1F1EF' }}>
                <tr>
                  <th style={{ padding: '10px', textAlign: 'left', fontSize: '12px' }}>#</th>
                  <th style={{ padding: '10px', textAlign: 'left', fontSize: '12px' }}>买家昵称</th>
                </tr>
              </thead>
              <tbody>
                {buyers.map((buyer, index) => (
                  <tr
                    key={buyer}
                    onClick={() => setSelectedBuyer(buyer)}
                    style={{
                      borderBottom: '1px solid #E9E9E7',
                      cursor: 'pointer',
                      backgroundColor: selectedBuyer === buyer ? '#E3F2FD' : 'transparent'
                    }}
                  >
                    <td style={{ padding: '10px', fontSize: '13px', color: '#787774' }}>{index + 1}</td>
                    <td style={{ padding: '10px', fontSize: '13px' }}>{buyer}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Selected Buyer Info */}
          {selectedBuyer && (
            <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#fff', border: '1px solid #E9E9E7', borderRadius: '4px' }}>
              <h3 style={{ fontSize: '16px', marginBottom: '10px', color: '#37352F' }}>已选择: {selectedBuyer}</h3>
              <p style={{ color: '#787774', fontSize: '13px' }}>这里可以显示买家详细画像（待实现）</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Metric Card Component
function MetricCard({ label, value, icon }: { label: string; value: number | string; icon: string }) {
  return (
    <div style={{
      backgroundColor: '#fff',
      border: '1px solid #E9E9E7',
      borderRadius: '4px',
      padding: '20px',
      boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
    }}>
      <div style={{ fontSize: '24px', marginBottom: '10px' }}>{icon}</div>
      <div style={{ fontSize: '12px', color: '#787774', marginBottom: '5px' }}>{label}</div>
      <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#37352F' }}>{value}</div>
    </div>
  );
}

// Priority Badge Component
function PriorityBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    'High': '#FEF2F2',
    'Medium': '#FEF3C7',
    'Low': '#ECFDF5',
    'Churn Risk': '#FEF2F2',
    'Negative Review': '#FEF2F2',
    'Stockout Request': '#FEF3C7',
    'Gift Inquiry': '#ECFDF5',
    'High Value': '#DBEAFE',
  };

  const textColors: Record<string, string> = {
    'High': '#991B1B',
    'Medium': '#92400E',
    'Low': '#075985',
    'Churn Risk': '#991B1B',
    'Negative Review': '#991B1B',
    'Stockout Request': '#92400E',
    'Gift Inquiry': '#075985',
    'High Value': '#1E40AF',
  };

  const bgColor = colors[type] || '#F3F4F6';
  const textColor = textColors[type] || '#37352F';

  return (
    <span style={{
      padding: '4px 8px',
      borderRadius: '3px',
      fontSize: '11px',
      fontWeight: '500',
      backgroundColor: bgColor,
      color: textColor
    }}>
      {type}
    </span>
  );
}

export default AppDemo;
