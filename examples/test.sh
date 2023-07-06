#!/bin/sh


/sbin/sendmail -t -oi <<EOF
To: Test List <test-list@andrewyu.org>
From: Andrew Yu <andrew@andrewyu.org>
Subject: Test Email
Message-ID: <$RANDOM@test>

This is a test email to test the functioning of the SMLMP Mailing List
management software and the archiving system used, if any.

From is the first word of this line. Yes, "From". SMLMP is expected not
to mangle this line.

Sometime we'll add more things to test in this test email.
EOF
