import sys
import os

from astropy.table import Table
from astropy.coordinates import SkyCoord
from astropy import units as u


def write_request(f, entry):
    if entry['period'] == 1:
        if entry['count'] > 3:
            project = 'Dwell on Targets'
        else:
            project = 'Monitor Every {:d} Days'.format(entry['period'])
    else:
        project = 'Monitor Every {:d} Days'.format(entry['period'])
    c = SkyCoord('{} {}'.format(entry['ra'], entry['dec']),
                 unit=(u.hourangle, u.deg),
                 frame='icrs',
                 equinox='J2000',
                 )
    f.write('   <Request bestefforts="false">\n')
    f.write('       <ID>{}</ID>\n'.format(entry['name']))
    f.write('       <UserName>VYSOS-5</UserName>\n')
    f.write('       <Description>Observing Plan for {}</Description>\n'.format(entry['name']))
    f.write('       <Reason>Monitor={:d}</Reason>\n'.format(entry['period']))
    f.write('       <Project>{}</Project>\n'.format(project))
    f.write('       <Schedule>\n')
    f.write('           <Horizon>{:.1f}</Horizon>\n'.format(entry['horizon']))
    f.write('           <Moon>\n')
    f.write('               <Distance>{:.1f}</Distance>\n'.format(entry['moond']))
    f.write('               <Width>{:.1f}</Width>\n'.format(entry['moonw']))
    f.write('           </Moon>\n')
    f.write('           <Priority>{:d}</Priority>\n'.format(entry['priority']))
    f.write('       </Schedule>\n')
    f.write('       <Target count="{:d}" interval="0" tolerance="0">\n'.format(entry['count']))
    f.write('           <Name>{}</Name>\n'.format(entry['name']))
    f.write('           <Coordinates>\n')
    f.write('               <RightAscension>{:+.4f}</RightAscension>\n'.format(c.ra.degree))
    f.write('               <Declination>{:+.4f}</Declination>\n'.format(c.dec.degree))
    f.write('           </Coordinates>\n')
    f.write('           <Picture count="{:d}">\n'.format(entry['nexp']))
    f.write('               <Name>PSr3</Name>\n')
    f.write('               <ExposureTime>{:.1f}</ExposureTime>\n'.format(entry['exptime']))
    f.write('               <Filter>{}</Filter>\n'.format(entry['filter']))
    f.write('               <Dither>4</Dither>\n')
    f.write('           </Picture>\n')
    f.write('       </Target>\n')
    f.write('   </Request>\n')
    f.write('\n')


if __name__ == '__main__':
    tab = Table.read('V5_targets.txt', format='ascii')
    rtml_file = 'V5_targets.rtml'
    if os.path.exists(rtml_file): os.remove(rtml_file)
    with open(rtml_file, 'w') as f:
        ## Header
        f.write('\n')
        f.write('<RTML>\n')
        f.write('   <Contact>\n')
        f.write('       <User>VYSOS-5</User>\n')
        f.write('       <Email>vysostelescope@gmail.com</Email>\n')
        f.write('   </Contact>\n')
        f.write('\n')
        bymonitor = tab.group_by('period')
        for entry in bymonitor:
            write_request(f, entry)
        f.write('</RTML>\n')

