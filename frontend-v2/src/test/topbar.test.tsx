import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '../context/ThemeContext';
import { AuthProvider } from '../context/AuthContext';
import { Topbar } from '../components/Topbar';

describe('Topbar Theme Toggle', () => {
  it('renders and toggles the document theme attribute when clicked', () => {
    render(
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <Topbar />
          </BrowserRouter>
        </AuthProvider>
      </ThemeProvider>
    );
    const button = screen.getByTitle('Toggle color theme');
    expect(button).toBeInTheDocument();
    
    const initialTheme = document.documentElement.getAttribute('data-theme');
    fireEvent.click(button);
    const newTheme = document.documentElement.getAttribute('data-theme');
    expect(newTheme).not.toBe(initialTheme);
  });
});
