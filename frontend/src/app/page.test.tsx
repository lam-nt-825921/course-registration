import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach, Mock } from 'vitest';
import Home from './page';
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

describe('Home Page', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    useAuthStore.setState({ studentId: '20020001', token: 'mock-token', role: 'student' });
  });

  const renderComponent = () => {
    const queryClient = createTestQueryClient();
    return render(
      <QueryClientProvider client={queryClient}>
        <Home />
      </QueryClientProvider>
    );
  };

  it('renders loading state initially', () => {
    (global.fetch as Mock).mockImplementation(() => new Promise(() => {}));
    
    renderComponent();
    
    expect(screen.getAllByText('Đang tải...').length).toBeGreaterThan(0);
  });

  it('renders courses and timetable successfully', async () => {
    const mockCourses = [
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
      },
    ];

    (global.fetch as Mock).mockImplementation(async (url: string) => {
      if (url.includes('/api/courses/my-schedule')) {
        return {
          ok: true,
          json: async () => mockCourses, // Registered course
        };
      }
      return {
        ok: true,
        json: async () => mockCourses,
      };
    });

    renderComponent();

    await waitFor(() => {
      // Course in the list, preview, and timetable
      const elements = screen.getAllByText('INT3110_1');
      expect(elements.length).toBeGreaterThan(1);
    });
  });
});
