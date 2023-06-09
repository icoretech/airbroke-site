import Image from 'next/image'
import Background from './Background';
import screenshot from '@/public/screenshot.png';
import Link from 'next/link';
import { FaGithub } from 'react-icons/fa';
import CurrentYear from './CurrentYear';
import logo from '@/public/logo.svg';

export default function Home() {
  return (
    <div className="h-full bg-gray-900">
      <div className="relative isolate overflow-hidden bg-gray-900">
        <Background />
        <div className="mx-auto max-w-7xl px-6 pb-24 pt-10 sm:pb-32 lg:flex lg:px-8 lg:py-40">
          <div className="mx-auto max-w-2xl flex-shrink-0 lg:mx-0 lg:max-w-xl lg:pt-8">
          <Image src={logo} alt="Airbroke logo" className="h-11 w-auto" />
            <div className="mt-24 sm:mt-32 lg:mt-16">
              <Link href="https://github.com/icoretech/airbroke/releases" className="inline-flex space-x-6">
                <span className="rounded-full bg-indigo-500/10 px-3 py-1 text-sm font-semibold leading-6 text-indigo-400 ring-1 ring-inset ring-indigo-500/20">
                  Latest Releases
                </span>
              </Link>
            </div>
            <h1 className="mt-10 text-4xl font-bold tracking-tight text-white sm:text-6xl">
              Hello, welcome to Airbroke
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-300">
              Self-hosted, Cost-effective, Open Source Error Tracking for a Sustainable Startup Journey.
            </p>
            <div className="mt-10 flex items-center gap-x-6">
              <a
                href="https://github.com/icoretech/airbroke/blob/main/README.md#deployment-options"
                className="rounded-md bg-indigo-500 px-3.5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400"
              >
                Setup Guide
              </a>
              <Link href="https://github.com/icoretech/airbroke/blob/main/README.md" className="text-sm font-semibold leading-6 text-white">
                Learn more <span aria-hidden="true">→</span>
              </Link>
            </div>
          </div>
          <div className="mx-auto mt-16 flex max-w-2xl sm:mt-24 lg:ml-10 lg:mr-0 lg:mt-0 lg:max-w-none lg:flex-none xl:ml-32">
            <div className="max-w-3xl flex-none sm:max-w-5xl lg:max-w-none">
              <Image
                src={screenshot}
                alt="Airbroke screenshot"
                className="w-[76rem] rounded-md bg-white/5 shadow-2xl ring-1 ring-white/10"
              />
            </div>
          </div>
        </div>
      </div>
      <footer className="bg-gray-900">
        <div className="mx-auto max-w-7xl px-6 py-12 md:flex md:items-center md:justify-between lg:px-8">
          <div className="flex justify-center space-x-6 md:order-2">
            <Link href="https://github.com/icoretech/airbroke" className="text-white hover:text-gray-500">
              <span className="sr-only">github</span>
              <FaGithub className="h-6 w-6" aria-hidden="true" />
            </Link>
          </div>
          <div className="mt-8 md:order-1 md:mt-0">
            <CurrentYear />
          </div>
        </div>
      </footer>
    </div>
    )
}
