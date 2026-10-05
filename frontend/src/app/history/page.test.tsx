import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach, Mock } from 'vitest';
import HistoryPage from './page';
import { useAuthStore } from '@/store/useAuthStore';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

// Mock fetch
global.fetch = vi.fn();

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe('History Page', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    useAuthStore.setState({ studentId: '20020001', token: 'mock-token' });
  });

  const renderComponent = () => {
    const queryClient = createTestQueryClient();
    return render(
      <QueryClientProvider client={queryClient}>
        <HistoryPage />
      </QueryClientProvider>
    );
  };

  it('renders loading state initially', () => {
    (global.fetch as Mock).mockImplementation(() => new Promise(() => {}));
    
    renderComponent();
    
    expect(screen.getByText('Đang tải lịch sử đăng ký...')).toBeInTheDocument();
  });

  it('renders enrollment history successfully', async () => {
    const mockHistory = [
      {
        semester_code: '20231',
        course_classes: [
          {
            id: '1',
            class_code: 'INT3110_1',
            course_code: 'INT3110',
            credits: 3,
            course_type: 'normal',
            max_capacity: 40,
            current_capacity: 10,
            schedules: [
              {
                day_of_week: 2,
                start_period: 1,
                end_period: 3,
              },
            ],
          }
        ]
      },
    ];

    (global.fetch as Mock).mockImplementation(async () => {
      return {
        ok: true,
        json: async () => mockHistory,
      };
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Kỳ học: 20231')).toBeInTheDocument();
      expect(screen.getByText('INT3110 - INT3110_1')).toBeInTheDocument();
      expect(screen.getByText('T2 (1-3)')).toBeInTheDocument();
    });
  });

  it('handles empty history list', async () => {
    (global.fetch as Mock).mockImplementation(async () => {
      return {
        ok: true,
        json: async () => [],
      };
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Chưa có dữ liệu lịch sử đăng ký.')).toBeInTheDocument();
    });
  });
});
