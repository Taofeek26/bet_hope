'use client';

import { HelpCircle, Book, MessageCircle, Mail, ExternalLink, ChevronRight, Zap, Target, BarChart3, Shield } from 'lucide-react';
import { useState } from 'react';

export default function HelpPage() {
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);

  const faqs = [
    {
      // Phase 0: the previous answer claimed 87% (95%+ for high
      // confidence). The measured figure on held-out matches is about
      // 49–50% (backend/models/*/metadata.json), and even strong football
      // models rarely beat ~55% on home/draw/away.
      question: 'How accurate are the predictions?',
      answer: 'On matches the model had not seen during training, it picks the correct result (home win, draw or away win) about 49–50% of the time. For comparison, simply backing the bookmakers\' favourite is right about 50–54% of the time, and even strong football models rarely go above 55%. Higher-confidence picks are right more often than low-confidence ones; the Analytics page shows the live record. We are rebuilding the model to improve this, and this figure will be updated when it changes.',
    },
    {
      question: 'What data sources do you use?',
      answer: 'Historical results, match statistics and pre-match average bookmaker odds come from Football-Data.co.uk. Upcoming fixtures, recent results and team crests come from the Football-Data.org API. Odds for upcoming matches and expected-goals (xG) data are not connected yet.',
    },
    {
      question: 'How are value bets calculated?',
      answer: 'Value bets are identified when our model calculates a higher probability of an outcome than what the bookmaker odds imply. An edge of 5%+ indicates potential value. For example, if we predict a 60% chance but odds imply only 50%, that\'s a 10% edge.',
    },
    {
      question: 'Which leagues are supported?',
      answer: 'Historical data covers 20 leagues. New fixtures and results currently arrive for 8 of them: Premier League, Championship, La Liga, Serie A, Bundesliga, Ligue 1, Eredivisie and Primeira Liga (plus the Champions League and Europa League). The other leagues show their most recent imported season until their live data source is added.',
    },
    {
      question: 'How often are predictions updated?',
      answer: 'Fixtures and results are synced once a day, the model is retrained daily, and predictions for the next 14 days are regenerated right after. Live in-play scores are not available yet, so a match shows its final score after the next daily sync.',
    },
    {
      question: 'Is this gambling advice?',
      answer: 'No. Bet Hope provides statistical predictions for educational and entertainment purposes only. We do not encourage gambling. Always gamble responsibly and only bet what you can afford to lose.',
    },
  ];

  return (
    <>
      <div className="content-header">
        <h1>Help Center</h1>
        <p>Get help and learn more about Bet Hope</p>
      </div>

      <div className="content-grid">
        {/* Quick Links */}
        <div className="col-span-12">
          <div className="grid grid-cols-4 gap-4 mb-8">
            <QuickLink
              icon={Book}
              title="Documentation"
              description="Learn how to use Bet Hope"
              href="#docs"
            />
            <QuickLink
              icon={MessageCircle}
              title="FAQ"
              description="Common questions answered"
              href="#faq"
            />
            <QuickLink
              icon={Zap}
              title="Features"
              description="Explore all features"
              href="#features"
            />
            <QuickLink
              icon={Mail}
              title="Contact"
              description="Get in touch with us"
              href="#contact"
            />
          </div>
        </div>

        {/* Features Section */}
        <div className="col-span-12" id="features">
          <div className="card mb-8">
            <div className="card-header">
              <div className="card-icon">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <h2 className="card-title">Key Features</h2>
                <p className="card-desc">What Bet Hope offers</p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-6">
              <FeatureCard
                icon={Target}
                title="AI Predictions"
                description="Machine learning model trained on several seasons of football data that estimates the chance of a home win, draw or away win for each match."
              />
              <FeatureCard
                icon={BarChart3}
                title="Analytics"
                description="Comprehensive statistics and performance tracking to help you understand prediction accuracy and trends."
              />
              <FeatureCard
                icon={Shield}
                title="Value Bets"
                description="Flags matches where the model's probability is at least 5 points above the bookmaker's implied probability. Needs bookmaker odds for the match, which upcoming fixtures don't have yet."
              />
            </div>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="col-span-12" id="faq">
          <div className="card">
            <div className="card-header">
              <div className="card-icon">
                <HelpCircle className="w-5 h-5" />
              </div>
              <div>
                <h2 className="card-title">Frequently Asked Questions</h2>
                <p className="card-desc">Find answers to common questions</p>
              </div>
            </div>

            <div className="space-y-3">
              {faqs.map((faq, index) => (
                <div
                  key={index}
                  className="border border-border-dim rounded-lg overflow-hidden"
                >
                  <button
                    onClick={() => setExpandedFaq(expandedFaq === index ? null : index)}
                    className="w-full flex items-center justify-between p-4 text-left hover:bg-surface transition-colors"
                  >
                    <span className="font-medium text-text">{faq.question}</span>
                    <ChevronRight
                      className={`w-5 h-5 text-text-muted transition-transform ${
                        expandedFaq === index ? 'rotate-90' : ''
                      }`}
                    />
                  </button>
                  {expandedFaq === index && (
                    <div className="px-4 pb-4 text-sm text-text-sec leading-relaxed">
                      {faq.answer}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Contact Section */}
        <div className="col-span-12" id="contact">
          <div className="card">
            <div className="card-header">
              <div className="card-icon">
                <Mail className="w-5 h-5" />
              </div>
              <div>
                <h2 className="card-title">Contact Us</h2>
                <p className="card-desc">Need more help? Get in touch</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div className="p-6 bg-surface rounded-lg border border-border-dim">
                <h3 className="font-semibold text-text mb-2">Report an Issue</h3>
                <p className="text-sm text-text-muted mb-4">
                  Found a bug or have feedback? Open an issue on GitHub.
                </p>
                <a
                  href="https://github.com/your-org/bet-hope/issues"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-secondary"
                >
                  <ExternalLink className="w-4 h-4" />
                  Open Issue
                </a>
              </div>

              <div className="p-6 bg-surface rounded-lg border border-border-dim">
                <h3 className="font-semibold text-text mb-2">General Inquiries</h3>
                <p className="text-sm text-text-muted mb-4">
                  For general questions and support, send us an email.
                </p>
                <a
                  href="mailto:support@bet-hope.com"
                  className="btn btn-primary"
                >
                  <Mail className="w-4 h-4" />
                  Email Support
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function QuickLink({ icon: Icon, title, description, href }: {
  icon: any;
  title: string;
  description: string;
  href: string;
}) {
  return (
    <a
      href={href}
      className="card card-compact hover:border-brand transition-colors group"
    >
      <div className="flex items-center gap-4">
        <div className="card-icon">
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <h3 className="font-semibold text-text group-hover:text-brand">{title}</h3>
          <p className="text-xs text-text-muted">{description}</p>
        </div>
      </div>
    </a>
  );
}

function FeatureCard({ icon: Icon, title, description }: {
  icon: any;
  title: string;
  description: string;
}) {
  return (
    <div className="p-6 bg-surface rounded-lg border border-border-dim">
      <div className="card-icon mb-4">
        <Icon className="w-5 h-5" />
      </div>
      <h3 className="font-semibold text-text mb-2">{title}</h3>
      <p className="text-sm text-text-muted">{description}</p>
    </div>
  );
}
