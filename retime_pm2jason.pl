#! /home/utils/perl-5.14/5.14.1-threads-64/bin/perl

use strict ;
use Carp;
use NVEnv;
use CadConfig;
use Data::Dumper ;
use JSON ;

#################
# Env & Vars 
#################

if ($#ARGV != -1) {
    help() ;
}

my %in_rules         = () ;
my %in_interf        = () ;
my $chiplet_uc       = "" ;

my $config = CadConfig::factory();
my $litter = $config->{LITTER_NAME} ;
my $proj   = $config->{NVPROJECT} ;
my $tot    = `depth` ;

my @all_uc_chiplets  = sort keys %{$config->{partitioning}{chiplets}} ;
my @all_chiplets     = () ;
my @all_interf_files = () ;

foreach my $uc_chiplet (@all_uc_chiplets) {
    if (exists $config->{partitioning}{chiplets}{$uc_chiplet}{retime}) {
        my $chiplet = $config->{partitioning}{chiplets}{$uc_chiplet}{retime} ;
        $chiplet =~ s/(\S+):\S+/$1/ ; 
        push @all_chiplets, $chiplet ;
    }  
}

#################################
# Parsing interface & routeRules 
#################################

my $interf_dir = "$tot/ip/retime/retime/1.0/vmod/include/interface_retime" ;
system "p4 sync $interf_dir/..." ; 

foreach my $chiplet (@all_chiplets) {
    @all_interf_files = glob "${interf_dir}/interface_retime_${litter}_${chiplet}_*.pm" ;
    $chiplet_uc = $chiplet ;
    foreach my $interf_file (@all_interf_files) {
        if (-e $interf_file) {
            do "$interf_file" ;
        }
    }
    print "Loaded files for $chiplet ...\n" ;
}


####################
# Dumping json file 
####################

my $json             = new JSON ;
my $rule_json        = $json->pretty->encode(\%in_rules) ;
my $interf_json      = $json->pretty->encode(\%in_interf) ;
my $json_dir         = "$tot/timing/$proj/timing_scripts/workflow/retime_detour_support" ;
my $rule_json_file   = "$json_dir/routeRules.json" ; 
my $interf_json_file = "$json_dir/interface.json" ; 

system "mkdir -p $json_dir" ;

open OUT, "> $rule_json_file" ;
print OUT "$rule_json" ;
close OUT ;
print "Retime routeRules : $rule_json_file\n" ;

open OUT, "> $interf_json_file" ;
print OUT "$interf_json" ;
close OUT ;
print "Retime interface  : $interf_json_file\n" ;


#################
# Subs  
#################

sub AddRouteRule { 
    my %in = @_ ;

    my $rule_name = $in{name} ;
    foreach my $key (sort keys %in) {
        $in_rules{$chiplet_uc}{$rule_name}{$key} = $in{$key} ;
    }
}

sub AddInterface {
    my %in = @_ ;
    my $rule_name = $in{pipelining} ;
    $rule_name =~ s/\S+:(\S+)/$1/ ;
    foreach my $key (sort keys %in) {
        $in_interf{$chiplet_uc}{$rule_name}{$key} = $in{$key} ;
    }
}

sub help {
    open(PAGER, "| more");
    print PAGER <<EndOfHelp;
Purpose:   To transfer all the retime routeRules and interface informations to json format.

Usage:     retime_pm2jason.pl
Example:   retime_pm2jason.pl

EndOfHelp
    close(PAGER);
    die "\n";
}

