'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import { BRAND_ASSETS } from '@/lib/constants/brand';

export type LogoVariant = 'horizontal' | 'icon';
export type LogoTheme = 'orange' | 'navy' | 'white';

export interface LogoProps {
  variant?: LogoVariant;
  theme?: LogoTheme;
  className?: string;
  width?: number;
  height?: number;
  priority?: boolean;
  alt?: string;
}

const THEME_MAP: Record<LogoTheme, 'ORANGE' | 'NAVY' | 'WHITE'> = {
  orange: 'ORANGE',
  navy: 'NAVY',
  white: 'WHITE',
};

const FALLBACK_TEXT_COLOR: Record<LogoTheme, string> = {
  orange: 'text-[#FF8F33]',
  navy: 'text-[#001046]',
  white: 'text-white',
};

export function Logo({
  variant = 'horizontal',
  theme = 'orange',
  className = '',
  width,
  height,
  priority = false,
  alt = 'PalmsGig',
}: LogoProps) {
  const [hasError, setHasError] = useState(false);

  const themeKey = THEME_MAP[theme];
  const src =
    variant === 'horizontal'
      ? BRAND_ASSETS.logos.horizontal[themeKey]
      : BRAND_ASSETS.logos.icon[themeKey];

  const defaultWidth = variant === 'horizontal' ? 160 : 40;
  const defaultHeight = variant === 'horizontal' ? 40 : 40;

  const resolvedWidth = width ?? defaultWidth;
  const resolvedHeight = height ?? defaultHeight;

  if (hasError) {
    return (
      <span
        role="img"
        aria-label={alt}
        className={`inline-flex items-center font-bold ${FALLBACK_TEXT_COLOR[theme]} ${className}`}
        style={{ width: resolvedWidth, height: resolvedHeight }}
      >
        PalmsGig
      </span>
    );
  }

  return (
    <Image
      src={src}
      alt={alt}
      width={resolvedWidth}
      height={resolvedHeight}
      priority={priority}
      onError={() => setHasError(true)}
      className={className}
      unoptimized
    />
  );
}

export default Logo;
