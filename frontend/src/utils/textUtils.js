// Utility function to detect Persian/Arabic text
export const isPersianText = (text) => {
  if (!text || typeof text !== 'string') return false;
  // Persian/Arabic Unicode ranges:
  // \u0600-\u06FF: Arabic block
  // \u0750-\u077F: Arabic Supplement
  // \u08A0-\u08FF: Arabic Extended-A
  // \uFB50-\uFDFF: Arabic Presentation Forms-A
  // \uFE70-\uFEFF: Arabic Presentation Forms-B
  const persianRegex = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
  return persianRegex.test(text);
};

// Helper function to extract text from React children
export const extractTextFromChildren = (children) => {
  if (typeof children === 'string') {
    return children;
  }
  if (typeof children === 'number') {
    return String(children);
  }
  if (children === null || children === undefined) {
    return '';
  }
  if (Array.isArray(children)) {
    return children.map(extractTextFromChildren).join('');
  }
  if (typeof children === 'object') {
    // Handle React elements
    if (children.props && children.props.children !== undefined) {
      return extractTextFromChildren(children.props.children);
    }
    // Handle other objects - try to stringify
    try {
      return String(children);
    } catch (e) {
      return '';
    }
  }
  return String(children || '');
};

