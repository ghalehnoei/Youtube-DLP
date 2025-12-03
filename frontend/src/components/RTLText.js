import React from 'react';
import { isPersianText, extractTextFromChildren } from '../utils/textUtils';

// Component to render text with RTL support for Persian
const RTLText = ({ children, className = '', tag: Tag = 'span' }) => {
  const text = extractTextFromChildren(children);
  const hasPersian = isPersianText(text);
  
  // Apply RTL styles inline as well to ensure they work
  const rtlStyle = hasPersian ? {
    direction: 'rtl',
    textAlign: 'right',
    unicodeBidi: 'embed'
  } : {};
  
  return (
    <Tag 
      className={className}
      dir={hasPersian ? 'rtl' : 'ltr'}
      style={rtlStyle}
    >
      {children}
    </Tag>
  );
};

export default RTLText;

