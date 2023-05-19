'use client';

export default function CurrentYear() {
  const currentYear = new Date().getFullYear();

  return (
    <p className="text-center text-xs leading-5 text-white">&copy; {currentYear} iCoreTech, Inc.</p>
  )
}
